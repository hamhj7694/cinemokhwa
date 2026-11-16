"""씨네목화 엔진 — P1 코어 파이프라인 (M-A 실사).

단계: script → keyframes → clips → assemble
각 단계는 독립 실행 가능하고, `work/<run_id>/state.json`으로 재개한다.
"""

__version__ = "0.2.0"
__all__ = [
    "assemble", "comfy", "config", "errors", "i2v", "keyframe", "project",
    "script", "verify",
]
