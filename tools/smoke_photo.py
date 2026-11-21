"""P2 실사 이미지 스모크 테스트 — Krea2 / Qwen21 중 하나를 1장 생성.

사용: python tools/smoke_photo.py krea2
      python tools/smoke_photo.py qwen21
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.comfy import Comfy  # noqa: E402
from engine.config import Config  # noqa: E402
from engine import photo  # noqa: E402

model = sys.argv[1] if len(sys.argv) > 1 else "krea2"
cfg = Config()
cfg.validate_image_model()  # noqa — 기본 모델 확인
# 스모크 테스트는 빠르게 768×432
cfg.width, cfg.height = 768, 432
comfy = Comfy(cfg)

prompt = (
    "photorealistic cinematic film still, 35mm lens, a tired Korean man in his "
    "late 30s standing in a narrow rainy Seoul alley at night, neon reflections "
    "on wet asphalt, natural skin texture, subtle film grain, shallow depth of field"
)
negative = "anime, illustration, plastic skin, waxy face, blurry, deformed hands, watermark, text"

flow = photo.build_workflow(
    cfg, model=model, prompt=prompt, negative=negative,
    seed=101, prefix=f"cinemokhwa/smoke_{model}",
)
print(f"[smoke] {model} workflow nodes: {len(flow)}")
t0 = time.time()
record = comfy.run(flow, f"P2 smoke {model}", timeout_s=900)
files = comfy.materialize(record, Path(cfg.root) / "work" / "smoke")
print(f"[smoke] elapsed {time.time() - t0:.1f}s")
for f in files:
    print(f"[smoke] OUTPUT {f}")
