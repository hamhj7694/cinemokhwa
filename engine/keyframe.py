"""키프레임 — SDXL(RealVisXL V5) 4시드 생성 후 중앙 40% 선명도 최고 선택.

P0에서 확정된 방식 그대로다: 후보 4장(24초/장) → 중앙 40% 라플라시안 분산 최대 →
그 1장을 I2V 입력으로 쓴다. 전역 선명도는 의도된 보케를 흐림으로 오판한다(ENVIRONMENT §6).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import numpy as np
from PIL import Image

from . import project as project_mod
from .comfy import Comfy
from .config import Config
from .errors import CineError
from .script import KEYFRAME_NEGATIVE, STYLES, anchor_text

SEEDS = (101, 202, 303, 404)
_REGION = 0.4


def prompt_for(project: project_mod.Project, scene: dict) -> str:
    """bible 앵커 + 화면 설명 + 화풍. 앵커가 인물·장소·조명을 씬 사이에 고정한다."""
    style = STYLES.get(project.style, STYLES["cinematic"])
    anchors = anchor_text(project.bible(), list(scene.get("anchors") or []))
    parts = [p for p in (anchors, scene["visual"]) if p]
    return f"{', '.join(parts)}, {style['suffix']}"


def reference_target(project: project_mod.Project, scene: dict) -> tuple[int, str] | None:
    """컷 장면이 참조할 **앞 장면 id**. 같은 인물(`char:`)이 나온 가장 가까운 장면.

    파일이 아직 없어도 대상을 먼저 정한다. 대본만 보고 결정되므로 캐시 키가
    "키프레임이 이미 생성됐는지"에 흔들리지 않는다. 실제 경로는 `reference_path()`.
    """
    anchors = [a for a in scene.get("anchors") or [] if str(a).startswith("char:")]
    if not anchors:
        return None
    for other in reversed(project.scenes()):
        if int(other["id"]) >= int(scene["id"]):
            continue
        if set(anchors) & set(other.get("anchors") or []):
            return int(other["id"]), f"keyframe{int(other['id']):02d}"
    return None


def reference_path(project: project_mod.Project, target_id: int) -> Path | None:
    """참조 대상 장면의 키프레임 파일. 없으면 그 클립의 첫 프레임으로 대체.

    키프레임을 먼저 쓰는 이유: 그 장면 외형의 기준값이고, 클립 첫 프레임은 그
    키프레임을 MAE ≤ 2.15로 재현한 결과라(D57) 거의 같다. 클립 프레임을 먼저 쓰면
    "새 run"과 "클립이 있는 run의 재생성"이 다른 참조를 쓰게 되어 재현성이 깨진다.
    """
    keyframe = project.keyframe_path(target_id)
    if keyframe.exists():
        return keyframe
    first = sorted((project.frames / f"scene_{target_id:02d}").glob("*.png"))
    return first[0] if first else None


def reference_for(project: project_mod.Project, scene: dict) -> tuple[Path | None, str]:
    """`reference_target()` + `reference_path()` 편의 함수(파일이 없으면 (None, ""))."""
    target = reference_target(project, scene)
    if target is None:
        return None, ""
    path = reference_path(project, target[0])
    return (path, target[1]) if path is not None else (None, "")


def _laplacian_var(path: Path) -> tuple[float, float]:
    """(전역, 중앙 40%) 라플라시안 분산. K = [[0,1,0],[1,-4,1],[0,1,0]]."""
    gray = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    p = np.pad(gray, 1, mode="edge")
    conv = (
        1.0 * p[0:-2, 1:-1]
        + 1.0 * p[1:-1, 0:-2]
        - 4.0 * p[1:-1, 1:-1]
        + 1.0 * p[1:-1, 2:]
        + 1.0 * p[2:, 1:-1]
    )
    h, w = gray.shape
    ch, cw = int(h * _REGION), int(w * _REGION)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    center = conv[y0 : y0 + ch, x0 : x0 + cw]
    return float(conv.var()) * 65025.0, float(center.var()) * 65025.0


def build_workflow(
    cfg: Config,
    prompt: str,
    negative: str,
    seed: int,
    prefix: str,
    *,
    reference: tuple[str, str] | None = None,
    layout: str | None = None,
) -> dict:
    """SDXL 키프레임 1장. `reference=(mode, 업로드된 이미지 이름)`.

    mode: "ipadapter" — 참조 이미지를 CLIP vision 임베딩으로 주입(인물 고정)
          "img2img"   — 참조 이미지를 잠재로 인코딩하고 denoise를 낮춰 변형(폴백)

    D67/D68: `layout`(업로드된 블록아웃 PNG)이 있으면 **정체성은 IPAdapter 참조,
    구도는 레이아웃 img2img 잠재**로 동시에 주입한다. 레이아웃이 latent를 덮어쓴다.
    """
    flow: dict = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": cfg.sdxl_ckpt},
        },
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative},
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": prefix},
        },
    }
    model: list = ["1", 0]
    latent: list = ["4", 0]
    denoise = 1.0

    mode, image = reference if reference else ("", "")

    if mode in ("ipadapter", "img2img"):
        flow["8"] = {"class_type": "LoadImage", "inputs": {"image": image}}

    if mode == "ipadapter":
        flow["9"] = {
            "class_type": "IPAdapterUnifiedLoader",
            "inputs": {"model": ["1", 0], "preset": cfg.ipadapter_preset},
        }
        flow["10"] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["9", 0],
                "ipadapter": ["9", 1],
                "image": ["8", 0],
                "weight": cfg.ipadapter_weight,
                "weight_type": "linear",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": "V only",
            },
        }
        model = ["10", 0]
        latent = ["4", 0]

    if mode == "img2img":
        # 참조 해상도가 설정과 다를 수 있으므로(중간에 크기를 바꾼 run) 먼저 맞춘다.
        flow["12"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["8", 0],
                "upscale_method": "lanczos",
                "width": cfg.width,
                "height": cfg.height,
                "crop": "center",
            },
        }
        flow["11"] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["12", 0], "vae": ["1", 2]},
        }
        latent = ["11", 0]
        denoise = cfg.img2img_denoise

    if layout:
        # D67: 3D 블록아웃을 구도 잠재로 주입한다. 위 IPAdapter 모델은 그대로 유지된다.
        flow["20"] = {"class_type": "LoadImage", "inputs": {"image": layout}}
        flow["21"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["20", 0],
                "upscale_method": "lanczos",
                "width": cfg.width,
                "height": cfg.height,
                "crop": "center",
            },
        }
        flow["22"] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["21", 0], "vae": ["1", 2]},
        }
        latent = ["22", 0]
        denoise = cfg.img2img_denoise

    flow["4"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": cfg.width, "height": cfg.height, "batch_size": 1},
    }
    flow["5"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": latent,
            "seed": seed,
            "steps": cfg.keyframe_steps,
            "cfg": cfg.cfg_scale,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": denoise,
        },
    }
    return flow


def stage_key(
    cfg: Config,
    project: project_mod.Project,
    scene: dict,
    reference: Path | None = None,
    *,
    ref_target: int | None = None,
    ref_digest: str | None = None,
    ref_card: str | None = None,
    layout_digest: str | None = None,
) -> str:
    """키프레임 캐시 키.

    `ref_target`(앞 장면 id)을 주면 파일 해시 대신 **대상 장면 id**를 쓴다. 같은 실행
    안에서 앞 장면 키프레임이 아직 없을 때도 키가 안정적이기 때문이다. 대상이 이번
    실행에서 다시 생성되지 않을 때(예: `--scene 3`)만 `ref_digest`로 내용을 반영한다.

    D66 ①: `ref_card`(`char:<id>`)를 주면 캐릭터 카드를 참조한다는 뜻이다. 카드는
    키프레임보다 먼저 만들어지므로 파일 해시를 쓸 수 있고, 카드가 바뀌면 키도 바뀐다.
    """
    if ref_card is not None:
        ref_part: object = {"card": str(ref_card), "digest": ref_digest or ""}
    elif ref_target is not None:
        ref_part = {"target": int(ref_target), "digest": ref_digest or ""}
    else:
        ref_part = project_mod.file_digest(reference) if reference else "none"
    return project_mod.digest(
        {
            "stage": "keyframe",
            "visual": scene["visual"],
            "anchors": anchor_text(project.bible(), list(scene.get("anchors") or [])),
            "seeds": SEEDS,
            "steps": cfg.keyframe_steps,
            "size": [cfg.width, cfg.height],
            "style": project.style,
            "ckpt": cfg.sdxl_ckpt,
            "ref": ref_part,
            "ref_mode": (
                cfg.kf_reference
                if (reference or ref_target is not None or ref_card is not None)
                else "none"
            ),
            "layout": layout_digest or "none",  # D67 — 3D 구도 해시
        }
    )


def generate(
    cfg: Config,
    comfy: Comfy,
    project: project_mod.Project,
    scene: dict,
    *,
    reference: Path | None = None,
    reference_label: str = "",
    layout: Path | None = None,
    force: bool = False,
) -> tuple[Path, dict]:
    """SDXL 4시드 → 최고 1장. `reference`=정체성(D66), `layout`=3D 구도(D67)."""
    if cfg.kf_reference not in ("ipadapter", "img2img"):
        reference, reference_label = None, ""   # CINEMOKHWA_KF_REF=none
    dest = project.keyframe_path(scene["id"])
    if dest.exists() and not force:
        return dest, {
            "cached": True,
            "file": dest.name,
            "reference": reference_label if reference is not None else "",
            "reference_mode": cfg.kf_reference if reference is not None else "none",
            "layout": layout.name if layout is not None else "",
        }

    prompt = prompt_for(project, scene)
    t0 = time.time()
    best: tuple[Path, int, float] | None = None
    candidates: list[dict] = []
    used_mode = "none"
    modes = []
    if reference is not None and cfg.kf_reference in ("ipadapter", "img2img"):
        modes = [cfg.kf_reference]
        if cfg.kf_reference == "ipadapter":
            modes.append("img2img")   # 폴백(D64)

    uploaded = comfy.upload_image(reference) if reference is not None else ""
    uploaded_layout = comfy.upload_image(layout) if layout is not None and layout.exists() else ""

    failed: set[str] = set()
    for seed in SEEDS:
        prefix = f"cinemokhwa/{project.run_id}/kf{scene['id']:02d}_s{seed}"
        record = None
        attempts = [m for m in (modes or ["none"]) if m not in failed]
        for attempt, mode in enumerate(attempts):
            ref = (mode, uploaded) if mode != "none" else None
            workflow = build_workflow(
                cfg, prompt, KEYFRAME_NEGATIVE, seed, prefix,
                reference=ref, layout=uploaded_layout or None,
            )
            label = f"키프레임 {scene['id']:02d} s{seed}"
            if mode != "none":
                label += f" · 참조 {mode} ({reference_label})"
            if uploaded_layout:
                label += f" · 3D구도 ({layout.name})"
            if attempt:
                label += " · 폴백"
            try:
                record = comfy.run(workflow, label, timeout_s=900)
                used_mode = mode
                break
            except CineError as exc:
                if attempt + 1 >= len(attempts):
                    raise
                failed.add(mode)   # 다음 시드부터는 이 방식으로 재시도하지 않는다
                print(f"      참조 {mode} 실패 → 폴백 ({exc.code})", flush=True)
        files = comfy.materialize(record, project.dir / "tmp")
        if not files:
            raise CineError(
                "RENDER-003",
                f"키프레임 산출물이 없습니다 (장면 {scene['id']}, 시드 {seed})",
            )
        full, center = _laplacian_var(files[0])
        candidates.append({"seed": seed, "center": round(center, 1), "full": round(full, 1)})
        if best is None or center > best[2]:
            best = (files[0], seed, center)

    assert best is not None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(best[0], dest)
    meta = {
        "seed": best[1],
        "center_sharpness": round(best[2], 1),
        "candidates": candidates,
        "file": dest.name,
        "reference": reference_label,
        "reference_mode": used_mode,
        "layout": layout.name if layout is not None else "",
        "elapsed": round(time.time() - t0, 1),
    }
    return dest, meta
