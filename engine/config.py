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

    # --- 모델 파일명 (ENVIRONMENT §3.1) ---
    sdxl_ckpt: str = "RealVisXL_V5.0_fp16.safetensors"
    wan_unet: str = "wan2.2_ti2v_5B_fp16.safetensors"
    wan_clip: str = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    wan_vae: str = "wan2.2_vae.safetensors"

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

    def scene_count(self, target_seconds: float) -> int:
        """M-A는 클립 5초 고정 → 완성 길이를 5초 단위로 올림."""
        import math

        return max(1, math.ceil(target_seconds / self.clip_seconds))

    def ensure_dirs(self) -> None:
        for d in (self.work, self.logs):
            d.mkdir(parents=True, exist_ok=True)
