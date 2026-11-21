"""P2 LTX-2.5 영상 스모크 테스트 — 25프레임 생성 시간/VRAM 측정.

사용: python tools/smoke_animate.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.animate import FPS, SIGMAS_8, build_workflow, STAGE1_W, STAGE1_H  # noqa: E402
from engine.comfy import Comfy  # noqa: E402
from engine.config import Config  # noqa: E402

cfg = Config()
comfy = Comfy(cfg)

prompt = (
    "photorealistic cinematic film still, 35mm lens, a tired Korean man in his "
    "late 30s standing in a narrow rainy Seoul alley at night, neon reflections "
    "on wet asphalt, natural skin texture, subtle film grain, slow subtle head turn"
)
negative = "anime, illustration, plastic skin, waxy face, blurry, deformed, watermark, text"

flow = build_workflow(
    cfg, prompt=prompt, negative=negative, seed=101, frames=25,
    prefix="cinemokhwa/smoke_ltx",
)
print(f"[smoke] LTX workflow nodes: {len(flow)}  {STAGE1_W}x{STAGE1_H} {FPS}fps 25f")
print(f"[smoke] sigmas: {SIGMAS_8}")
t0 = time.time()
record = comfy.run(flow, "P2 smoke LTX 25f", timeout_s=3600)
files = comfy.materialize(record, Path(cfg.root) / "work" / "smoke")
elapsed = time.time() - t0
print(f"[smoke] elapsed {elapsed:.1f}s ({elapsed/25*121/60:.1f}분 예상@121f)")
for f in files:
    print(f"[smoke] OUTPUT {f} ({f.stat().st_size/1e6:.1f}MB)")
