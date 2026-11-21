"""P2 L0/L2 — 실사 이미지 생성 (Krea 2 / Qwen-Image 2.1 / SDXL 드롭다운).

3D는 틀만 담당한다. 이 모듈이 **외형·정체성·질감**의 유일한 원본이다.

| model | DiT | 텍스트 인코더 | 스텝 | 참조 주입 |
|---|---|---|---|---|
| krea2 (기본) | GGUF Q5_K_S (GGUF 포크) | qwen3vl_4b fp8 | 8 | img2img 잠재 (denoise 0.55) |
| qwen21 | int8_convrot | qwen3vl_8b w4a8 | 8 | TextEncodeQwenImage21 reference images (최대 10) |
| sdxl | RealVisXL | 내장 | 32 | IPAdapter (레거시) |

생성물은 `face_gate`와 육안 확인을 모두 통과해야 앵커로 쓴다.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from PIL import Image

from . import keyframe, project as project_mod
from .comfy import Comfy
from .config import Config
from .errors import CineError

# Krea 2 turbo 권장값(공식 블루프린트): 8 steps, cfg 1, euler, simple.
KREA_STEPS = 8
KREA_CFG = 1.0
# Qwen-Image 2.1 turbo LoRA 권장값: 8 steps, cfg 1, shift 3.1.
QWEN_STEPS = 8
QWEN_CFG = 1.0
QWEN_SHIFT = 3.1
KREA_DENOISE = 0.55   # 참조 앵커를 살리면서 포즈/각도는 바꾸는 정도


def prompt_for(cfg: Config, project: project_mod.Project, scene: dict) -> str:
    """대본의 구도/앵커 + AI 티 제거 프롬프트."""
    base = keyframe.prompt_for(project, scene)
    return f"{base}, {cfg.photoreal_positive}"


def negative_for(cfg: Config, scene: dict | None = None) -> str:
    extra = keyframe.KEYFRAME_NEGATIVE if scene is not None else ""
    parts = [p for p in (extra, cfg.photoreal_negative) if p]
    return ", ".join(parts)


def stage_key(
    cfg: Config,
    project: project_mod.Project,
    scene: dict,
    *,
    refs: list[Path] | None = None,
) -> str:
    model = cfg.validate_image_model()
    ref_parts = [project_mod.file_digest(p) if p.exists() else "missing" for p in (refs or [])]
    return project_mod.digest({
        "stage": "p2_photo",
        "model": model,
        "prompt": prompt_for(cfg, project, scene),
        "negative": negative_for(cfg, scene),
        "visual": scene.get("visual", ""),
        "size": [cfg.width, cfg.height],
        "seeds": keyframe.SEEDS,
        "refs": ref_parts,
        "version": "p2-v1",
    })


def build_workflow(
    cfg: Config,
    *,
    model: str,
    prompt: str,
    negative: str,
    seed: int,
    prefix: str,
    references: list[str] | None = None,
) -> dict:
    """모델별 ComfyUI API 워크플로 1장. `references`는 업로드된 이미지 이름."""
    refs = list(references or [])
    flow: dict = {}

    if model == "krea2":
        flow["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": cfg.krea2_dit}}
        flow["2"] = {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": cfg.krea2_clip, "type": "krea2", "device": "cpu",
            },
        }
        flow["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": cfg.krea2_vae}}
        flow["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}}
        pos_node = "4"
        neg_node = "5"
        flow["5"] = {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["4", 0]},
        }
        vae = ["3", 0]
        latent: list = ["6", 0]
        flow["6"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": cfg.width, "height": cfg.height, "batch_size": 1},
        }
        if refs:
            flow["7"] = {"class_type": "LoadImage", "inputs": {"image": refs[0]}}
            flow["8"] = {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["7", 0], "vae": vae},
            }
            latent = ["8", 0]
        denoise = KREA_DENOISE if refs else 1.0
        steps, sampler, scheduler = KREA_STEPS, "euler", "simple"
        model_out = ["1", 0]

    elif model == "qwen21":
        flow["1"] = {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": cfg.qwen21_dit, "weight_dtype": "default"},
        }
        flow["2"] = {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": cfg.qwen21_clip, "type": "qwen_image", "device": "cpu",
            },
        }
        flow["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": cfg.qwen21_vae}}
        model_out = ["1", 0]
        # Turbo LoRA가 있으면 8스텝 경로를 쓴다. 없으면 원본 모델 경로(느림).
        turbo = cfg.models / "loras" / cfg.qwen21_turbo_lora
        if turbo.exists():
            flow["9"] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "model": model_out,
                    "lora_name": cfg.qwen21_turbo_lora,
                    "strength_model": 1.0,
                },
            }
            model_out = ["9", 0]
        flow["10"] = {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": model_out, "shift": QWEN_SHIFT},
        }
        model_out = ["10", 0]
        images: dict[str, list] = {}
        for i, name in enumerate(refs[:10]):
            flow[str(30 + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}
            images[f"image_{i + 1}"] = [str(30 + i), 0]
        flow["4"] = {
            "class_type": "TextEncodeQwenImage21",
            "inputs": {
                "clip": ["2", 0],
                "prompt": prompt,
                "negative_prompt": negative,
                "resolution": cfg.width,
                "images": images,
                "vae": ["3", 0],
            },
        }
        pos_node, neg_node = "4", "4"   # 같은 노드의 0/1 출력
        flow["6"] = {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": cfg.width, "height": cfg.height, "batch_size": 1},
        }
        latent = ["6", 0]
        denoise = 1.0
        steps, sampler, scheduler = QWEN_STEPS, "euler", "simple"

    elif model == "sdxl":
        flow["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": cfg.sdxl_ckpt}}
        flow["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}}
        flow["5"] = {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}}
        pos_node, neg_node = "4", "5"
        model_out = ["1", 0]
        vae = ["1", 2]
        flow["6"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": cfg.width, "height": cfg.height, "batch_size": 1},
        }
        latent = ["6", 0]
        if refs:
            flow["7"] = {"class_type": "LoadImage", "inputs": {"image": refs[0]}}
            flow["8"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["7", 0], "vae": vae}}
            latent = ["8", 0]
        denoise = 0.55 if refs else 1.0
        steps, sampler, scheduler = cfg.keyframe_steps, "dpmpp_2m", "karras"

    else:
        raise CineError("CFG-003", f"알 수 없는 이미지 모델: {model}")

    flow["11"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_out,
            "seed": seed,
            "steps": steps,
            "cfg": KREA_CFG if model in ("krea2", "qwen21") else cfg.cfg_scale,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "positive": [pos_node, 0],
            "negative": [neg_node, 0 if model != "qwen21" else 1],
            "latent_image": latent,
            "denoise": denoise,
        },
    }
    decode_vae = ["3", 0] if model in ("krea2", "qwen21") else ["1", 2]
    flow["12"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["11", 0], "vae": decode_vae},
    }
    flow["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": prefix}}
    return flow


def generate(
    cfg: Config,
    comfy: Comfy,
    project: project_mod.Project,
    scene: dict,
    *,
    references: list[Path] | None = None,
    dest: Path | None = None,
    force: bool = False,
) -> tuple[Path, dict]:
    """실사 키프레임 1장 생성. 여러 시드 중 얼굴 게이트 통과분을 우선 채택."""
    model = cfg.validate_image_model()
    if model == "qwen21":
        # Qwen Research License — 상업 산출물에는 쓸 수 없다(문서에 명시).
        pass
    refs = [p for p in (references or []) if p.exists()]
    dest = dest or project.keyframe_path(scene["id"])
    if dest.exists() and not force:
        return dest, {"cached": True, "model": model, "file": dest.name}

    prompt = prompt_for(cfg, project, scene)
    negative = negative_for(cfg, scene)
    uploaded = [comfy.upload_image(p) for p in refs]
    prefix = f"cinemokhwa/{project.run_id}/p2_{model}_{scene['id']:02d}"
    t0 = time.time()
    candidates: list[dict] = []
    for seed in keyframe.SEEDS:
        flow = build_workflow(
            cfg, model=model, prompt=prompt, negative=negative,
            seed=seed, prefix=f"{prefix}_s{seed}", references=uploaded,
        )
        record = comfy.run(flow, f"P2 사진 장면 {scene['id']:02d} s{seed}", timeout_s=900)
        files = comfy.materialize(record, project.dir / "tmp")
        if not files:
            raise CineError("RENDER-003", f"실사 이미지 산출물 없음 (장면 {scene['id']}, 시드 {seed})")
        candidates.append({"seed": seed, "path": files[0]})

    # 얼굴 게이트는 보조 지표. 얼굴이 없는 컷(소품·배경만)은 통과 처리하고
    # 얼굴이 있는 컷은 기준 앵커와 유사한 것부터 쓴다.
    from . import facegate

    ref_face = refs[0] if refs else None
    scored: list[dict] = []
    for c in candidates:
        sim = None
        if ref_face is not None and facegate.DEFAULT_MODEL_DIR.exists():
            try:
                sim = facegate.similarity(ref_face, c["path"])
            except Exception:  # noqa: BLE001 — ONNX/모델 문제로 전체를 멈추지 않는다
                sim = None
        scored.append({**c, "face_similarity": sim})
    usable = [c for c in scored if c["face_similarity"] is None
              or c["face_similarity"] >= cfg.face_gate_pass]
    pool = usable or scored
    # 유사도 최고 → 중앙 선명도 순. 최종 합격은 사람이 contact sheet로 확인한다.
    def rank(c: dict):
        _, center = keyframe._laplacian_var(c["path"])
        return (-(c["face_similarity"] if c["face_similarity"] is not None else -1.0), -center)

    chosen = min(pool, key=rank)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(chosen["path"], dest)
    meta = {
        "model": model,
        "seed": chosen["seed"],
        "face_similarity": chosen["face_similarity"],
        "gate_count": len(usable),
        "candidates": [
            {"seed": c["seed"], "sim": c["face_similarity"]} for c in scored
        ],
        "references": [p.name for p in refs],
        "elapsed": round(time.time() - t0, 1),
        "visual_review": "REQUIRED",
    }
    return dest, meta
