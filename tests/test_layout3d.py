"""D67 레이아웃 패스 오프라인 테스트 — 모델·ComfyUI 불필요."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import layout3d  # noqa: E402

BIBLE = {
    "characters": [{"id": "jun", "desc": "man in grey coat", "ref": "references/char_jun.png"}],
    "places": [{"id": "alley", "desc": "wet Seoul alley"}],
    "look": "rainy night",
}
SCENES = [
    {"id": 1, "shot": "S1", "anchors": ["char:jun", "place:alley"],
     "visual": "wide shot, a man walks down a wet alley", "motion": "slow dolly forward"},
    {"id": 2, "shot": "S1", "anchors": ["char:jun"],
     "visual": "same man, camera closer behind his shoulder", "motion": "following"},
    {"id": 3, "shot": "S2", "anchors": ["char:jun"],
     "visual": "medium close up of the same man under neon", "motion": "static"},
]


class Fake:
    style = "cinematic"
    run_id = "unit"

    def __init__(self, root):
        self.dir = root
        (root / "layouts").mkdir(parents=True, exist_ok=True)

    def bible(self):
        return BIBLE


root = Path(tempfile.mkdtemp())
proj = Fake(root)

# 1) 결정성 — 같은 입력이 같은 Scene3D
a = layout3d.build_scene(proj, SCENES[0], 0)
b = layout3d.build_scene(proj, SCENES[0], 0)
assert a == b
print("PASS: Scene3D 결정성")

# 2) 컷별 구도 차이가 실제로 반영
s1 = layout3d.build_scene(proj, SCENES[0], 0)
s2 = layout3d.build_scene(proj, SCENES[1], 1)
s3 = layout3d.build_scene(proj, SCENES[2], 2)
assert s1.features["wide"] and not s3.features["wide"]
assert s3.features["close"]
assert s2.features["behind"] and abs(s2.figures[0].heading - 3.14159) < 0.01
assert s1.camera.target[2] > s3.camera.target[2]  # 원경 카메라 시점이 더 멀다
print("PASS: wide/close/behind → 카메라 거리·heading 반영")

# 3) 투사 — 정면 중앙의 점은 화면 중앙 부근
center = layout3d.project((0.0, 1.4, 6.0), s3.camera, 1280, 704)
assert center is not None and abs(center[0] - 640) < 2, center
assert layout3d.project((0.0, 1.4, -1.0), s3.camera, 1280, 704) is None
print("PASS: 원근 투사 + 후면 클리핑")

# 4) 렌더 — 크기/결정성
img1 = layout3d.render(s1, 320, 176)
img2 = layout3d.render(s1, 320, 176)
assert img1.size == (320, 176)
assert img1.tobytes() == img2.tobytes()
print("PASS: 블록아웃 렌더 크기·바이트 결정성")

# 5) 캐시 — 같은 키면 cached, force면 재생성
p1, m1 = layout3d.generate(proj, SCENES[0], sequence=0, width=320, height=176)
p2, m2 = layout3d.generate(proj, SCENES[0], sequence=0, width=320, height=176)
assert p1 == p2 and m2["cached"]
_, m3 = layout3d.generate(proj, SCENES[0], sequence=0, width=320, height=176, force=True)
assert not m3.get("cached")
print("PASS: 레이아웃 캐시/force 재생성")

# 6) 캐시키 — 구도가 바뀌면 키가 달라짐
assert layout3d.stage_key(proj, SCENES[0], 0) != layout3d.stage_key(proj, SCENES[2], 2)
print("PASS: 레이아웃 캐시키")

# 7) Blender export — 같은 Scene3D가 스크립트에 담김
out = layout3d.export_blender(s1, root / "layout_blender.py")
text = out.read_text(encoding="utf-8")
data = json.loads(text.split('r"""', 1)[1].split('"""', 1)[0])
assert data["scene_id"] == 1 and len(data["figures"]) == 1
assert "bpy.ops.render.render" in text
print("PASS: Blender export(동일 좌표계)")

# 8) 이중 참조 — 정체성(IPAdapter) + 구도(레이아웃 img2img)가 동시에 연결
from engine import keyframe  # noqa: E402
from engine.config import Config  # noqa: E402

flow = keyframe.build_workflow(
    Config(), "visual", "negative", 101, "test",
    reference=("ipadapter", "card.png"), layout="layout.png",
)
assert flow["10"]["class_type"] == "IPAdapterAdvanced"
assert flow["20"]["inputs"]["image"] == "layout.png"
assert flow["22"]["class_type"] == "VAEEncode"
assert flow["5"]["inputs"]["model"] == ["10", 0]     # 정체성 = 카드
assert flow["5"]["inputs"]["latent_image"] == ["22", 0]  # 구도 = 레이아웃
k1 = keyframe.stage_key(Config(), proj, SCENES[0], ref_card="char:jun", layout_digest="aaa")
k2 = keyframe.stage_key(Config(), proj, SCENES[0], ref_card="char:jun", layout_digest="bbb")
assert k1 != k2
assert abs(flow["5"]["inputs"]["denoise"] - Config().layout_denoise) < 1e-6
print("PASS: IPAdapter(정체성) + 레이아웃 img2img(구도) 동시 주입 + 캐시키 반영")

# 9) D70 설정 — Blender가 기본 백엔드이고 실행 파일이 실제로 존재
cfg = Config()
assert cfg.layout_backend == "blender", cfg.layout_backend
assert cfg.blender_exe.exists(), cfg.blender_exe
print("PASS: D70 기본 백엔드=blender · Blender 실행 파일 존재")

# 10) 백엔드별 캐시키 분리 — CPU 도면과 Blender 도면이 섞이지 않아야 한다
k_cpu = layout3d.stage_key(proj, SCENES[0], 0, backend="cpu")
k_blender = layout3d.stage_key(proj, SCENES[0], 0, backend="blender")
assert k_cpu != k_blender
print("PASS: D70 백엔드별 캐시키 분리")

# 11) generate() 디스패치 — blender면 render_blender 호출, cpu면 호출 안 함
from unittest.mock import patch  # noqa: E402

with patch.object(layout3d, "render_blender", return_value=root / "layouts" / "layout_01.png") as rb:
    _, mb = layout3d.generate(proj, SCENES[0], sequence=0, width=320, height=176,
                              force=True, backend="blender")
assert rb.call_count == 1 and mb["backend"] == "blender"
with patch.object(layout3d, "render_blender") as rb2:
    _, mc = layout3d.generate(proj, SCENES[0], sequence=0, width=320, height=176,
                              force=True, backend="cpu")
assert rb2.call_count == 0 and mc["backend"] == "cpu"
print("PASS: D70 generate() 백엔드 디스패치")

print("\nALL PASS")
