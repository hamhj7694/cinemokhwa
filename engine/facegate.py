"""얼굴 정체성 게이트 — 숫자는 보조, 최종 판정은 사람 눈.

`tools/face_identity.py`(YuNet + SFace, Apache 2.0)를 단일 구현으로 재사용한다.
P2에서는 "같은 사람인지"를 넘기 위한 **필터**로만 쓴다.
게이트를 통과해도 contact sheet로 육안 확인해야 최종 합격이다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .config import Config
from .errors import CineError

_TOOLS = Path(__file__).resolve().parents[1] / "tools" / "face_identity.py"
DEFAULT_MODEL_DIR = Path(r"C:\Users\mbc\mokhwa\work\models\face")


def _module():
    spec = importlib.util.spec_from_file_location("cinemokhwa_face_identity", _TOOLS)
    if spec is None or spec.loader is None:
        raise CineError("DEP-010", f"얼굴 게이트 모듈을 읽을 수 없습니다: {_TOOLS}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def similarity(reference: Path, target: Path, model_dir: Path | None = None) -> float | None:
    """두 이미지의 얼굴 코사인 유사도. 얼굴이 없으면 None."""
    mod = _module()
    rows = mod.measure(reference, [target], model_dir or DEFAULT_MODEL_DIR)
    if not rows or not rows[0].get("face"):
        return None
    return float(rows[0]["similarity"])


def passes(cfg: Config, reference: Path, target: Path) -> tuple[bool, float | None]:
    """기준 사진과의 유사도가 임계값 이상인지. 임계값은 Config.face_gate_pass."""
    sim = similarity(reference, target)
    return (sim is not None and sim >= cfg.face_gate_pass), sim
