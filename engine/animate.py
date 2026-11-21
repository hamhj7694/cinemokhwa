"""P2 L3 — LTX-2.5 실사 영상화 (GGUF 12GB + 프레임 앵커).

역할 분리(D63~D72 3차 개정):
  - 3D(previs) : 카메라·위치·깊이·포즈 **틀**만
  - 사진(photo) : 인물·소품·배경의 **외형·정체성**
  - 이 모듈   : 위 두 결과를 **움직이는 실사 영상**으로 결합

핵심 설정(공식 LTX-2.5 distilled 권장):
  - DiT GGUF Q3(11GB) → OOM 시 Q2(8.9GB) 자동 fallback
  - 텍스트 인코더 gemma4 w4a8, video/audio VAE bf16
  - 8스텝 sigmas, euler_ancestral, CFG 1 (BasicGuider)
  - 프레임 앵커: LTXVImgToVideoInplace(첫 실사 프레임) +
                 LTXVAddGuide(3D 포즈/구도 프레임을 8n+1 간격으로 핀)
  - VAE 디코드는 tiled(512/64/128/32)로 12GB VRAM 보호

`visual_review: REQUIRED` — 숫자 PASS만으로 합격하지 않는다(D72).
"""

from __future__ import annotations

import time
from pathlib import Path

from . import project as project_mod
from .comfy import Comfy
from .config import Config
from .errors import CineError

# 공식 distilled 8스텝 sigmas (마지막 0은 깨끗한 수렴용)
SIGMAS_8 = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
FPS = 24
# 12GB 안전 설정: stage1 960×544. 최종 1280×704는 upscale 스테이지에서 맞춘다.
STAGE1_W, STAGE1_H = 960, 544
TILE = {"tile_size": 512, "overlap": 64, "temporal_size": 128, "temporal_overlap": 32}


def prompt_for(cfg: Config, project: project_mod.Project, scene: dict) -> str:
    from .photo import prompt_for as photo_prompt
    return photo_prompt(cfg, project, scene)


def build_workflow(
    cfg: Config,
    *,
    prompt: str,
    negative: str,
    seed: int,
    frames: int,
    dit: str | None = None,
    first_frame: str | None = None,
    anchors: list[tuple[str, int]] | None = None,
    prefix: str = "cinemokhwa/p2_clip",
) -> dict:
    """LTX-2.5 단일 스테이지 워크플로.

    `anchors` = [(업로드된 이미지 이름, 프레임 인덱스), ...]. 프레임 인덱스는
    8의 배수로 반올림된다(LTXVAddGuide 규칙). 3D 프리비즈 프레임을 여기 넣는다.
    """
    dit = dit or cfg.ltx_dit_loader
    flow: dict = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": dit}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": cfg.ltx_text_encoder, "type": "ltxv", "device": "cpu"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": cfg.ltx_video_vae}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": cfg.ltx_audio_vae}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "7": {"class_type": "LTXVConditioning", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "frame_rate": FPS}},
    }
    pos, neg = ["7", 0], ["7", 1]

    flow["8"] = {"class_type": "EmptyLTXVLatentVideo", "inputs": {
        "width": STAGE1_W, "height": STAGE1_H, "length": frames, "batch_size": 1}}

    # 첫 실사 프레임을 잠재에 직접 심는다 (정체성 앵커).
    if first_frame:
        flow["20"] = {"class_type": "LoadImage", "inputs": {"image": first_frame}}
        flow["21"] = {"class_type": "LTXVPreprocess", "inputs": {
            "image": ["20", 0], "img_compression": 35}}
        flow["22"] = {"class_type": "LTXVImgToVideoInplace", "inputs": {
            "vae": ["3", 0], "image": ["21", 0], "latent": ["8", 0],
            "strength": 1.0, "bypass": False}}
        latent = ["22", 2]
        pos, neg = ["22", 0], ["22", 1]
    else:
        latent = ["8", 0]

    # 3D 구도 프레임을 핀으로 고정 (IC-LoRA 없이 동작하는 fallback).
    for i, (name, frame_idx) in enumerate(anchors or []):
        base = 30 + i * 3
        flow[str(base)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        flow[str(base + 1)] = {"class_type": "LTXVPreprocess", "inputs": {
            "image": [str(base), 0], "img_compression": 35}}
        flow[str(base + 2)] = {"class_type": "LTXVAddGuide", "inputs": {
            "positive": pos, "negative": neg, "vae": ["3", 0], "latent": latent,
            "image": [str(base + 1), 0], "frame_idx": frame_idx, "strength": 1.0}}
        pos, neg, latent = [str(base + 2), 0], [str(base + 2), 1], [str(base + 2), 2]

    flow["90"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS_8}}
    flow["91"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}}
    # distilled CFG 1 → BasicGuider(positive만). CFGGuider(cfg=1)과 수학적으로 동일.
    flow["92"] = {"class_type": "BasicGuider", "inputs": {
        "model": ["1", 0], "conditioning": pos}}
    flow["93"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler_ancestral"}}
    flow["94"] = {"class_type": "SamplerCustomAdvanced", "inputs": {
        "noise": ["91", 0], "guider": ["92", 0], "sampler": ["93", 0],
        "sigmas": ["90", 0], "latent_image": latent}}
    flow["95"] = {"class_type": "VAEDecodeTiled", "inputs": {
        "samples": ["94", 0], "vae": ["3", 0], **TILE}}
    flow["96"] = {"class_type": "CreateVideo", "inputs": {
        "images": ["95", 0], "fps": FPS}}
    flow["97"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["96", 0], "filename_prefix": prefix, "format": "mp4"}}
    return flow


def generate(
    cfg: Config,
    comfy: Comfy,
    *,
    prompt: str,
    negative: str,
    seed: int,
    frames: int,
    first_frame: Path | None = None,
    anchor_frames: list[tuple[Path, int]] | None = None,
    dest: Path | None = None,
    label: str = "P2 클립",
) -> tuple[Path, dict]:
    """클립 1개 생성. OOM이면 Q2 GGUF로 자동 재시도한다."""
    if dest and dest.exists():
        return dest, {"cached": True, "file": dest.name}

    uploaded_first = comfy.upload_image(first_frame) if first_frame else None
    uploaded_anchors = [
        (comfy.upload_image(p), idx) for p, idx in (anchor_frames or [])
    ]

    t0 = time.time()
    attempts = [(cfg.ltx_dit_loader, None)]
    if cfg.ltx_dit_small:
        attempts.append((cfg.ltx_dit_small_loader, "OOM 대비 Q2 전환"))

    last_error: Exception | None = None
    for dit, note in attempts:
        flow = build_workflow(
            cfg, prompt=prompt, negative=negative, seed=seed, frames=frames,
            dit=dit, first_frame=uploaded_first, anchors=uploaded_anchors,
            prefix=f"cinemokhwa/p2_{seed}",
        )
        try:
            record = comfy.run(flow, f"{label} ({Path(dit).name})", timeout_s=3600)
            files = comfy.materialize(record, dest.parent if dest else None)
            if not files:
                raise CineError("RENDER-004", "영상 산출물 없음")
            out = files[0]
            if dest:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if out.resolve() != dest.resolve():
                    out.replace(dest)
                out = dest
            return out, {
                "dit": Path(dit).name, "note": note, "seed": seed, "frames": frames,
                "elapsed": round(time.time() - t0, 1), "visual_review": "REQUIRED",
            }
        except Exception as exc:  # noqa: BLE001 — OOM이면 다음 시도
            last_error = exc
            if note is None:
                continue
            break
    raise CineError("RENDER-005", f"LTX 생성 실패: {last_error}")
