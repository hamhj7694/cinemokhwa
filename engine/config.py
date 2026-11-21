"""경로·기본값의 단일 출처.

- D55: 엔진·모델·산출물은 `C:\\Users\\mbc\\mokhwa\\` (git 레포 밖)
- D57: 생성 기본값은 P0 실측으로 확정된 값만 넣는다
- D2 : 대본 LLM = gemma4:12b (2026-11-16 사용자 승인)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import CineError

DEFAULT_ROOT = r"C:\Users\mbc\mokhwa"

# P2 이미지 생성 모델 드롭다운 후보. CLI/UI는 이 목록을 그대로 노출한다.
IMAGE_MODELS = ("krea2", "qwen21", "sdxl")


@dataclass
class Config:
    root: Path = field(
        default_factory=lambda: Path(os.environ.get("CINEMOKHWA_ROOT") or DEFAULT_ROOT)
    )
    port: int = field(
        default_factory=lambda: int(os.environ.get("CINEMOKHWA_COMFY_PORT", "8188"))
    )
    ollama: str = field(
        default_factory=lambda: os.environ.get(
            "CINEMOKHWA_OLLAMA", "http://127.0.0.1:11434"
        ).rstrip("/")
    )
    llm_model: str = field(
        default_factory=lambda: os.environ.get("CINEMOKHWA_LLM", "gemma4:12b")
    )

    # --- 생성 기본값 (D57) ---
    width: int = 1280
    height: int = 704
    fps: int = 24
    keyframe_steps: int = 32
    i2v_steps: int = 20          # 25스텝=21.7분/5초. 20스텝=18분 → 15초 1편 ≤70분
    cfg_scale: float = 5.0
    shift: float = 8.0
    clip_seconds: float = 5.0    # M-A 클립 상한 (4k+1 규격)
    crossfade_seconds: float = 0.3
    crf: int = 16

    # --- 컷 사이 참조 주입 (D64) ---
    # "ipadapter" | "img2img" | "none". ipadapter가 실패하면 img2img로 자동 폴백한다.
    kf_reference: str = field(
        default_factory=lambda: os.environ.get("CINEMOKHWA_KF_REF", "ipadapter").strip().lower()
    )
    ipadapter_preset: str = "PLUS (high strength)"
    ipadapter_weight: float = 0.8
    img2img_denoise: float = 0.55

    # --- D67/D68 3D 레이아웃 주입 ---
    # 블록아웃을 구도 잠재로 넣을 때의 denoise. 낮을수록 도면 색이 남고,
    # 높을수록 구도 힌트만 남고 실사로 다시 칠해진다(육안 확인 후 조절).
    layout_denoise: float = field(
        default_factory=lambda: float(os.environ.get("CINEMOKHWA_LAYOUT_DENOISE", "0.70"))
    )

    # --- D70 Blender 백엔드 (2026-11-21 설치) ---
    # 무료 GPL · 로컬 headless 렌더. CPU 블록아웃보다 고주파 선이 적어
    # 실사 키프레임에 번지지 않는다. CINEMOKHWA_LAYOUT_BACKEND=blender|cpu
    layout_backend: str = field(
        default_factory=lambda: os.environ.get("CINEMOKHWA_LAYOUT_BACKEND", "blender").strip().lower()
    )
    blender_exe: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CINEMOKHWA_BLENDER") or r"C:\Users\mbc\mokhwa\apps\blender-4.5.16-windows-x64\blender.exe"
        )
    )

    # --- 모델 파일명 (ENVIRONMENT §3.1) ---
    sdxl_ckpt: str = "RealVisXL_V5.0_fp16.safetensors"
    wan_unet: str = "wan2.2_ti2v_5B_fp16.safetensors"
    wan_clip: str = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    wan_vae: str = "wan2.2_vae.safetensors"

    # --- P2 하이브리드 (3차 개정: 3D는 틀, 실사가 외형) ---
    # 이미지 생성 모델 드롭다운: krea2(기본) | qwen21 | sdxl(레거시)
    image_model: str = field(
        default_factory=lambda: os.environ.get("CINEMOKHWA_IMAGE_MODEL", "krea2").strip().lower()
    )
    # LTX-2.5 (GGUF + comfy-native w4a8 텍스트 인코더)
    ltx_dit: str = "ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf"
    ltx_dit_small: str = "ltx-2.5-22b-distilled-UD-Q2_K_XL.gguf"  # OOM 대비
    ltx_text_encoder: str = "gemma4-12b-ltx25-comfy-w4a8.safetensors"
    ltx_video_vae: str = "ltx-2.5-video-vae-conv-bf16.safetensors"
    ltx_audio_vae: str = "ltx-2.5-audio-vae-bf16.safetensors"
    ltx_spatial_upscaler: str = "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"
    ltx_layout_lora: str = "ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors"
    ltx_msr_lora: str = "LTX-2.5-Licon-MSR-V2.safetensors"

    # Krea 2 — GGUF DiT(city96 포크) + Qwen3VL 텍스트 인코더 + 공용 VAE
    krea2_dit: str = "Krea-2-Turbo-Q5_K_S.gguf"
    krea2_clip: str = "qwen3vl_4b_fp8_scaled.safetensors"
    krea2_vae: str = "qwen_image_vae.safetensors"
    # Qwen-Image 2.1 — comfy-native int8 + qwen3vl 8B w4a8 + Turbo LoRA
    qwen21_dit: str = "qwen_image_2.1_int8_convrot.safetensors"
    qwen21_clip: str = "qwen3vl_8b_w4a8.safetensors"
    qwen21_vae: str = "qwen_image_2.1_vae_bf16.safetensors"
    qwen21_turbo_lora: str = "qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors"

    # 얼굴 게이트 — 숫자는 보조. 최종 합격은 사람 눈으로 확인한다.
    face_gate_pass: float = 0.60

    # AI 티 제거 프롬프트 (3차 개정). 실사 사진/키프레임 생성에 공통 적용.
    photoreal_positive: str = (
        "photorealistic, shot on Sony A7R V, 85mm f/1.8, natural skin pores, "
        "subtle film grain, real-world lighting, candid documentary photograph"
    )
    photoreal_negative: str = (
        "3d render, CGI, cartoon, anime, illustration, plastic skin, oversaturated, "
        "airbrushed, AI artifact, blurry, watermark, text"
    )

    # ---------------------------------------------------------------- paths
    @property
    def host(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def comfy_portable(self) -> Path:
        return self.root / "ComfyUI_windows_portable"

    @property
    def comfy_dir(self) -> Path:
        return self.comfy_portable / "ComfyUI"

    @property
    def comfy_input(self) -> Path:
        return self.comfy_dir / "input"

    @property
    def comfy_output(self) -> Path:
        return self.comfy_dir / "output"

    @property
    def models(self) -> Path:
        return self.comfy_dir / "models"

    @property
    def python(self) -> Path:
        return self.comfy_portable / "python_embeded" / "python.exe"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ffmpeg(self) -> Path:
        override = os.environ.get("CINEMOKHWA_FFMPEG")
        if override:
            p = Path(override)
            if p.exists():
                return p
            raise CineError(
                "DEP-002",
                f"CINEMOKHWA_FFMPEG 경로가 없습니다: {p}",
                hint="환경 변수를 지우면 자동 탐색합니다.",
            )
        found = sorted((self.root / "tools" / "ffmpeg").glob("*/bin/ffmpeg.exe"))
        if not found:
            raise CineError(
                "DEP-002",
                "ffmpeg.exe를 찾지 못했습니다.",
                hint=r"ENVIRONMENT §2의 tools\ffmpeg 경로를 확인하거나 CINEMOKHWA_FFMPEG로 지정하세요.",
            )
        return found[-1]

    def ffprobe(self) -> Path:
        return self.ffmpeg().with_name("ffprobe.exe")

    # ---------------------------------------------------------------- utils
    def frames(self, seconds: float) -> int:
        """Wan 규격 length = 4k+1 (24fps에서 5초 = 121). 목표 이상으로 올림한다."""
        n = max(5, round(seconds * self.fps))
        k = -(-(n - 1) // 4)  # ceil
        return 4 * k + 1

    def model_files(self) -> list[tuple[str, Path]]:
        m = self.models
        return [
            ("SDXL 키프레임", m / "checkpoints" / self.sdxl_ckpt),
            ("Wan UNET", m / "diffusion_models" / self.wan_unet),
            ("Wan 텍스트 인코더", m / "text_encoders" / self.wan_clip),
            ("Wan VAE", m / "vae" / self.wan_vae),
        ]

    def validate_image_model(self) -> str:
        """드롭다운 값 검증. 잘못된 값은 설정 오류로 즉시 중단한다."""
        model = self.image_model.strip().lower()
        if model not in IMAGE_MODELS:
            raise CineError(
                "CFG-003",
                f"알 수 없는 이미지 모델: {self.image_model}",
                hint=f"가능한 값: {', '.join(IMAGE_MODELS)}",
            )
        return model

    @property
    def ltx_dit_loader(self) -> str:
        """ComfyUI UnetLoaderGGUF 드롭다운 값 (하위폴더 구분자 포함)."""
        return "distilled\\" + self.ltx_dit

    @property
    def ltx_dit_small_loader(self) -> str:
        """OOM 대비 Q2 GGUF의 ComfyUI 로더 이름."""
        return "distilled\\" + self.ltx_dit_small

    def p2_model_files(self) -> list[tuple[str, Path]]:
        """P2 파이프라인이 **반드시** 필요한 파일 목록 (env check용).

        Layout-to-Render LoRA는 HF 승인제라 없어도 되므로 `p2_optional_model_files()`로 분리했다.
        없으면 3D 구도를 프레임 앵커(LTXVAddGuide)로 직접 주입한다.
        """
        m = self.models
        model = self.validate_image_model()
        files = [
            ("LTX DiT", m / "unet" / "distilled" / self.ltx_dit),
            ("LTX 텍스트 인코더", m / "text_encoders" / self.ltx_text_encoder),
            ("LTX 영상 VAE", m / "vae" / self.ltx_video_vae),
            ("LTX 오디오 VAE", m / "vae" / self.ltx_audio_vae),
            ("LTX 업스케일러", m / "latent_upscale_models" / self.ltx_spatial_upscaler),
            ("MSR V2 LoRA", m / "loras" / self.ltx_msr_lora),
        ]
        if model == "krea2":
            files += [
                ("Krea2 DiT", m / "unet" / self.krea2_dit),
                ("Krea2 텍스트 인코더", m / "text_encoders" / self.krea2_clip),
                ("Krea2 VAE", m / "vae" / self.krea2_vae),
            ]
        elif model == "qwen21":
            files += [
                ("Qwen21 DiT", m / "diffusion_models" / self.qwen21_dit),
                ("Qwen21 텍스트 인코더", m / "text_encoders" / self.qwen21_clip),
                ("Qwen21 VAE", m / "vae" / self.qwen21_vae),
                ("Qwen21 Turbo LoRA", m / "loras" / self.qwen21_turbo_lora),
            ]
        else:
            files.append(("SDXL 체크포인트", m / "checkpoints" / self.sdxl_ckpt))
        return files

    def p2_optional_model_files(self) -> list[tuple[str, Path]]:
        """없어도 파이프라인이 동작하는 파일. 없으면 안내만 하고 계속 진행한다."""
        m = self.models
        return [
            ("Layout-to-Render LoRA (승인제)", m / "loras" / self.ltx_layout_lora),
            ("LTX DiT Q2 (OOM 대비)", m / "unet" / "distilled" / self.ltx_dit_small),
        ]

    def scene_count(self, target_seconds: float) -> int:
        """M-A는 클립 5초 고정 → 완성 길이를 5초 단위로 올림."""
        import math

        return max(1, math.ceil(target_seconds / self.clip_seconds))

    def ensure_dirs(self) -> None:
        for d in (self.work, self.logs):
            d.mkdir(parents=True, exist_ok=True)
