"""영상 생성 — Wan 2.2 TI2V-5B I2V (M-A 전용).

P0 확정 설정(D57)을 그대로 쓴다:
  ModelSamplingSD3 shift=8 · fp8_e4m3fn · uni_pc/simple · cfg 5 · length=4k+1
출력은 PNG 마스터 → FFmpeg CRF16 (SaveVideo의 기본 압축 통과 금지).

체이닝(D63/D65): 같은 `shot`의 다음 클립은 앞 클립 **마지막 프레임**을
`start_image`로 쓴다. 겹침은 0이다 — 실측에서 모델이 시작 프레임을 MAE 1.2로
거의 그대로 재현했고, 겹쳐 생성한 뒤 트림하면 그만큼 시간이 건너뛰었다(D65).
Wan 2.2 5B는 `start_image`만 받으므로 끝 프레임 지정은 쓰지 않는다.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from . import assemble
from . import project as project_mod
from .comfy import Comfy
from .config import Config
from .errors import CineError

I2V_NEGATIVE = (
    "blurry, low quality, distorted, warped face, extra fingers, static frame, jitter, "
    "flicker, text, watermark"
)

# 이전 클립과 겹쳐 생성한 뒤 버리는 프레임 수. D65 실측으로 0 확정.
#   0 : 시작 프레임이 1장 중복되지만 이음새 MAE 1.17 (기준 3.0 이내)
#   8 : 트림만큼 시간이 8프레임 건너뛰어 MAE 39.9~47.5 (실패)
CHAIN_OVERLAP = 0
CHAIN_MOTION = "continuous take, same lighting and colour as the previous shot"


def last_frame(frames_dir: Path, back: int = 0) -> Path:
    """프레임 폴더의 끝에서 `back`번째 장. 없으면 명확한 오류.

    체이닝은 기본(`CHAIN_OVERLAP = 0`)으로 마지막 프레임에서 시작한다.
    `back`은 겹침을 다시 켤 때(트림 후 시간 정렬) 쓰는 값이다.
    """
    files = sorted(frames_dir.glob("*.png"))
    if not files:
        raise CineError(
            "RENDER-008",
            f"이전 클립의 프레임이 없습니다: {frames_dir}",
            hint="앞 장면 클립을 먼저 생성하세요(--scene 재생성 시에도 앞 장면이 필요합니다).",
        )
    return files[max(0, len(files) - 1 - back)]


def _mae(a: Path, b: Path) -> float:
    """두 PNG의 그레이스케일 평균 절대 오차(0~255). 이음새 판정용.

    해상도가 다르면(중간에 --width를 바꾼 run) b를 a 크기로 맞춰 비교한다.
    """
    ia = Image.open(a).convert("L")
    ib = Image.open(b).convert("L")
    if ib.size != ia.size:
        ib = ib.resize(ia.size, Image.LANCZOS)
    ga = np.asarray(ia, dtype=np.float32)
    gb = np.asarray(ib, dtype=np.float32)
    return float(np.abs(ga - gb).mean())


def build_workflow(
    cfg: Config,
    image_name: str,
    prompt: str,
    negative: str,
    frames: int,
    seed: int,
    prefix: str,
) -> dict:
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": cfg.wan_unet, "weight_dtype": "fp8_e4m3fn"},
        },
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": cfg.wan_clip, "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": cfg.wan_vae}},
        "4": {
            "class_type": "ModelSamplingSD3",
            "inputs": {"model": ["1", 0], "shift": cfg.shift},
        },
        "5": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["2", 0], "text": negative},
        },
        "8": {
            "class_type": "Wan22ImageToVideoLatent",
            "inputs": {
                "vae": ["3", 0],
                "width": cfg.width,
                "height": cfg.height,
                "length": frames,
                "batch_size": 1,
                "start_image": ["5", 0],
            },
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["8", 0],
                "seed": seed,
                "steps": cfg.i2v_steps,
                "cfg": cfg.cfg_scale,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {
            "class_type": "SaveImage",
            "inputs": {"images": ["10", 0], "filename_prefix": prefix},
        },
    }


def expected_frames(cfg: Config, scene: dict) -> int:
    return cfg.frames(float(scene.get("seconds", cfg.clip_seconds)))


def stage_key(
    cfg: Config,
    project: project_mod.Project,
    scene: dict,
    keyframe: Path,
    chain_digest: str | None = None,
) -> str:
    return project_mod.digest(
        {
            "stage": "i2v",
            "keyframe": project_mod.file_digest(keyframe),
            "motion": scene["motion"],
            "frames": expected_frames(cfg, scene),
            "steps": cfg.i2v_steps,
            "size": [cfg.width, cfg.height],
            "shift": cfg.shift,
            "unet": cfg.wan_unet,
            "chain": chain_digest or "cut",
            "overlap": CHAIN_OVERLAP,
        }
    )


def generate(
    cfg: Config,
    comfy: Comfy,
    project: project_mod.Project,
    scene: dict,
    keyframe: Path,
    *,
    seed: int = 42,
    force: bool = False,
    chain_from: Path | None = None,
) -> tuple[Path, dict]:
    dest = project.clip_path(scene["id"])
    if dest.exists() and not force:
        return dest, {"cached": True}

    frames = expected_frames(cfg, scene)
    seconds = float(scene.get("seconds", cfg.clip_seconds))

    # 체이닝: 앞 클립 마지막 프레임을 시작 이미지로 쓴다. overlap은 기본 0이고,
    # 다시 켜면 앞 클립에서 overlap만큼 앞선 프레임에서 시작해 트림 후 시간을 맞춘다.
    start_image = keyframe
    overlap = 0
    seam_src: Path | None = None
    if chain_from is not None:
        overlap = CHAIN_OVERLAP
        seam_src = last_frame(chain_from)                    # 실제 앞 클립의 마지막
        start_src = last_frame(chain_from, back=overlap)      # 겹침만큼 앞선 프레임
        start_image = project.dir / "tmp" / f"chain_{project.run_id}_{scene['id']:02d}.png"
        start_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(start_src, start_image)

    total = cfg.frames(seconds + overlap / cfg.fps) if overlap else frames
    if total - overlap < frames:
        total = frames + overlap
    if (total - 1) % 4:  # 4k+1 규격 보정
        total += 4 - (total - 1) % 4

    image_name = comfy.upload_image(start_image)
    prefix = f"cinemokhwa/{project.run_id}/scene{scene['id']:02d}"
    motion = f"{scene['motion']}, {CHAIN_MOTION}" if chain_from is not None else scene["motion"]
    workflow = build_workflow(cfg, image_name, motion, I2V_NEGATIVE, total, seed, prefix)

    # 실측: 5초/20스텝=18분, 25스텝=21.7분 → 스텝당 0.72분 + 고정 3.6분
    estimate_min = (0.72 * cfg.i2v_steps + 3.6) * (total / frames) * (seconds / cfg.clip_seconds)
    timeout_s = estimate_min * 60 * 2.5 + 600

    record = comfy.run(
        workflow,
        f"I2V 장면 {scene['id']:02d} ({seconds:.1f}초, {total}프레임"
        + (f", 연장 {overlap}겹침" if overlap else (", 연장" if chain_from is not None else ""))
        + ")",
        timeout_s=timeout_s,
    )

    files = comfy.materialize(record, project.frames / f"scene_{scene['id']:02d}")
    if len(files) < overlap + frames:
        raise CineError(
            "RENDER-004",
            f"프레임이 부족합니다: {len(files)}/{overlap + frames} (장면 {scene['id']})",
            hint="ComfyUI 로그에서 SaveImage 노드 출력을 확인하세요.",
        )

    # 프레임을 씬 전용 폴더에 1..N으로 정규화한다.
    # (output/에는 이전 시도의 프레임이 남아 있을 수 있어 패턴만으로는 섞인다)
    frame_dir = project.frames / f"scene_{scene['id']:02d}"
    if frame_dir.exists():
        shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    kept = files[overlap : overlap + frames]
    for index, src in enumerate(kept, start=1):
        dst = frame_dir / f"{index:05d}.png"
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)

    seam = None
    if seam_src is not None:
        seam = round(_mae(seam_src, kept[0]), 2)

    dest.parent.mkdir(parents=True, exist_ok=True)
    assemble.encode_frames(str(frame_dir / "%05d.png"), dest, cfg)

    meta = {
        "frames": frames,
        "seconds": round(frames / cfg.fps, 3),
        "seed": seed,
        "steps": cfg.i2v_steps,
        "size": [cfg.width, cfg.height],
        "file": dest.name,
        "overlap": overlap,
        "seam_mae": seam,
    }
    return dest, meta
