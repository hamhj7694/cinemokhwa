"""영상 생성 — Wan 2.2 TI2V-5B I2V (M-A 전용).

P0 확정 설정(D57)을 그대로 쓴다:
  ModelSamplingSD3 shift=8 · fp8_e4m3fn · uni_pc/simple · cfg 5 · length=4k+1
출력은 PNG 마스터 → FFmpeg CRF16 (SaveVideo의 기본 압축 통과 금지).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import assemble
from . import project as project_mod
from .comfy import Comfy
from .config import Config
from .errors import CineError

I2V_NEGATIVE = (
    "blurry, low quality, distorted, warped face, extra fingers, static frame, jitter, "
    "flicker, text, watermark"
)


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


def stage_key(cfg: Config, project: project_mod.Project, scene: dict, keyframe: Path) -> str:
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
) -> tuple[Path, dict]:
    dest = project.clip_path(scene["id"])
    if dest.exists() and not force:
        return dest, {"cached": True}

    frames = expected_frames(cfg, scene)
    image_name = comfy.upload_image(keyframe)
    prefix = f"cinemokhwa/{project.run_id}/scene{scene['id']:02d}"
    workflow = build_workflow(cfg, image_name, scene["motion"], I2V_NEGATIVE, frames, seed, prefix)

    seconds = float(scene.get("seconds", cfg.clip_seconds))
    # 실측: 5초/20스텝=18분, 25스텝=21.7분 → 스텝당 0.72분 + 고정 3.6분
    estimate_min = (0.72 * cfg.i2v_steps + 3.6) * (seconds / cfg.clip_seconds)
    timeout_s = estimate_min * 60 * 2.5 + 600

    record = comfy.run(
        workflow,
        f"I2V 장면 {scene['id']:02d} ({seconds:.1f}초, {frames}프레임)",
        timeout_s=timeout_s,
    )

    files = comfy.materialize(record, project.frames / f"scene_{scene['id']:02d}")
    if len(files) < frames:
        raise CineError(
            "RENDER-004",
            f"프레임이 부족합니다: {len(files)}/{frames} (장면 {scene['id']})",
            hint="ComfyUI 로그에서 SaveImage 노드 출력을 확인하세요.",
        )

    # 프레임을 씬 전용 폴더에 1..N으로 정규화한다.
    # (output/에는 이전 시도의 프레임이 남아 있을 수 있어 패턴만으로는 섞인다)
    frame_dir = project.frames / f"scene_{scene['id']:02d}"
    if frame_dir.exists():
        shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    for index, src in enumerate(files[:frames], start=1):
        dst = frame_dir / f"{index:05d}.png"
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)

    dest.parent.mkdir(parents=True, exist_ok=True)
    assemble.encode_frames(str(frame_dir / "%05d.png"), dest, cfg)

    meta = {
        "frames": frames,
        "seconds": round(frames / cfg.fps, 3),
        "seed": seed,
        "steps": cfg.i2v_steps,
        "size": [cfg.width, cfg.height],
        "file": dest.name,
    }
    return dest, meta
