"""키프레임 — SDXL(RealVisXL V5) 4시드 생성 후 중앙 40% 선명도 최고 선택.

P0에서 확정된 방식 그대로다: 후보 4장(24초/장) → 중앙 40% 라플라시안 분산 최대 →
그 1장을 I2V 입력으로 쓴다. 전역 선명도는 의도된 보케를 흐림으로 오판한다(ENVIRONMENT §6).
"""

from __future__ import annotations

import shutil
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


def build_workflow(cfg: Config, prompt: str, negative: str, seed: int, prefix: str) -> dict:
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": cfg.sdxl_ckpt},
        },
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": cfg.width, "height": cfg.height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": cfg.keyframe_steps,
                "cfg": cfg.cfg_scale,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": prefix},
        },
    }


def stage_key(cfg: Config, project: project_mod.Project, scene: dict) -> str:
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
        }
    )


def generate(
    cfg: Config,
    comfy: Comfy,
    project: project_mod.Project,
    scene: dict,
    *,
    force: bool = False,
) -> tuple[Path, dict]:
    dest = project.keyframe_path(scene["id"])
    if dest.exists() and not force:
        return dest, {"cached": True}

    prompt = prompt_for(project, scene)
    best: tuple[Path, int, float] | None = None
    candidates: list[dict] = []

    for seed in SEEDS:
        prefix = f"cinemokhwa/{project.run_id}/kf{scene['id']:02d}_s{seed}"
        workflow = build_workflow(cfg, prompt, KEYFRAME_NEGATIVE, seed, prefix)
        record = comfy.run(workflow, f"키프레임 {scene['id']:02d} s{seed}", timeout_s=900)
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
    }
    return dest, meta
