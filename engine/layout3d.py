"""D67 — 결정론적 3D 레이아웃 패스 (Blender 설치 없이도 동작).

사용자 아이디어 1("Blender로 빠르게 3D 구도")을 완전 무료·로컬로 실현한다.
대본의 `anchors`/`visual`/`motion`에서 **같은 3D 좌표계**의 카메라·인물·배경을
결정론적으로 배치하고, numpy+PIL로 블록아웃 PNG를 그린다.

왜 소프트웨어 렌더인가
  - Blender가 이 PC에 없다(2026-11-21 확인). 설치/다운로드 없이 바로 동작해야 한다.
  - 목적은 "예쁜 3D"가 아니라 **구도 고정**이다. 선·실루엣만으로 충분하다.
  - Blender가 생기면 `export_blender()`로 같은 Scene3D를 그대로 렌더할 수 있다.

실사 텍스처는 기존 SDXL/Wan 레이어가 담당한다(D68). 새 모델·유료 API 없다(D39/D47).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import project as project_mod

WIDE = re.compile(
    r"\b(wide|long shot|extreme wide|establishing|from behind|behind (?:him|her)|"
    r"walks away|recedes|far away|back of)\b", re.IGNORECASE,
)
CLOSE = re.compile(
    r"\b(close[ -]?up|medium close|close shot|tight shot|portrait)\b", re.IGNORECASE,
)
CLOSER = re.compile(r"\b(closer|nearer|step closer|moves closer)\b", re.IGNORECASE)
BEHIND = re.compile(
    r"\b(from behind|behind (?:him|her|his|her|the) shoulder|behind (?:him|her)|"
    r"back of|walks away|turned away)\b", re.IGNORECASE,
)
DOLLY = re.compile(r"\b(dolly|push in|tracking|following|advance|moves? forward)\b", re.IGNORECASE)

# 블록아웃 팔레트 — SDXL이 구도를 읽기 쉽도록 대비를 준다.
C_SKY_TOP = (24, 28, 38)
C_SKY_BOT = (52, 58, 72)
C_GROUND = (44, 48, 58)
C_GRID = (48, 53, 65)   # 배경에 가까운 낮은 대비 — 선이 실사로 번지지 않게
C_BLOCK = (86, 104, 138)
C_BLOCK_EDGE = (130, 152, 190)
C_FIGURE = (236, 150, 84)
C_FIGURE_BACK = (150, 92, 60)
C_HEAD = (244, 206, 160)
C_HORIZON = (110, 120, 140)


@dataclass
class Camera:
    pos: tuple[float, float, float] = (0.0, 1.62, 0.0)
    target: tuple[float, float, float] = (0.0, 1.42, 6.0)
    fov: float = 55.0


@dataclass
class Figure:
    id: str
    pos: tuple[float, float, float]      # x, y(보통 0), z(깊이)
    height: float = 1.75
    heading: float = 0.0                 # 0 = 카메라를 봄, pi = 뒤돌아봄
    color: tuple[int, int, int] = C_FIGURE


@dataclass
class Block:
    pos: tuple[float, float, float]      # 박스 중심
    size: tuple[float, float, float]     # 가로, 세로, 깊이
    color: tuple[int, int, int] = C_BLOCK


@dataclass
class Scene3D:
    scene_id: int
    camera: Camera
    figures: list[Figure] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    features: dict = field(default_factory=dict)


# ------------------------------------------------------------------ 빌더
def build_scene(
    project: project_mod.Project,
    scene: dict,
    sequence: int = 0,
) -> Scene3D:
    """대본 한 장면 → 결정론적 3D 배치. 난수 없음."""
    visual = str(scene.get("visual") or "")
    motion = str(scene.get("motion") or "")
    text = f"{visual} {motion}"

    wide, close, closer = bool(WIDE.search(text)), bool(CLOSE.search(text)), bool(CLOSER.search(text))
    behind = bool(BEHIND.search(text))
    dolly = bool(DOLLY.search(text))

    # 카메라 거리: 원경 11m → 보통 6m → 근접 3m. 컷이 이어질수록 살짝 전진.
    depth = 11.0 if wide else (3.0 if close else (4.5 if closer else 6.0))
    if dolly:
        depth -= min(sequence, 3) * 0.35
    depth = max(2.2, depth)
    cam_y = 2.35 if wide else (1.5 if close else 1.62)

    cam = Camera(
        pos=(0.0, cam_y, 0.0),
        target=(0.0, 1.35 if not wide else 1.55, depth),
        fov=62.0 if wide else (48.0 if close else 55.0),
    )

    bible = project.bible()
    char_ids = [
        str(a)[5:].strip().lower()
        for a in (scene.get("anchors") or [])
        if str(a).startswith("char:")
    ]
    place_ids = [
        str(a)[6:].strip().lower()
        for a in (scene.get("anchors") or [])
        if str(a).startswith("place:")
    ]

    figures: list[Figure] = []
    for i, cid in enumerate(char_ids):
        x = (i - (len(char_ids) - 1) / 2.0) * 1.15
        figures.append(
            Figure(
                id=cid,
                pos=(x, 0.0, depth + 3.8),
                heading=math.pi if behind else 0.0,
                color=C_FIGURE_BACK if behind else C_FIGURE,
            )
        )

    # 배경: 골목이면 양쪽 건물, 그 외에도 좌우 블록을 두어 원근 기준선을 만든다.
    alley = any("alley" in p or "street" in p or "road" in p for p in place_ids)
    blocks: list[Block] = []
    if place_ids or figures:
        spread = 4.2 if alley else 5.2
        for side in (-1, 1):
            blocks.append(
                Block(
                    pos=(side * spread, 2.6, depth + 6.0),
                    size=(2.8 if alley else 3.6, 5.2, 17.0),
                )
            )
        if not alley:
            blocks.append(
                Block(pos=(0.0, 1.1, depth + 15.0), size=(7.0, 2.2, 1.2))
            )

    # 인물 카드 경로는 메타에만 기록(실제 참조는 character.card_for가 담당).
    card_refs = {
        str(c.get("id", "")).lower(): str(c.get("ref") or "")
        for c in (bible.get("characters") or [])
        if isinstance(c, dict)
    }
    return Scene3D(
        scene_id=int(scene.get("id", 0)),
        camera=cam,
        figures=figures,
        blocks=blocks,
        features={
            "wide": wide, "close": close, "closer": closer,
            "behind": behind, "dolly": dolly, "depth": round(depth, 2),
            "characters": char_ids, "places": place_ids,
            "card_refs": {k: card_refs.get(k, "") for k in char_ids},
        },
    )


# ------------------------------------------------------------------ 투사
def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n else v.copy()


def _basis(cam: Camera) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pos = np.asarray(cam.pos, dtype=float)
    forward = _norm(np.asarray(cam.target, dtype=float) - pos)
    right = _norm(np.cross(np.asarray((0.0, 1.0, 0.0)), forward))
    up = np.cross(forward, right)
    return right, up, forward


def project(
    point: tuple[float, float, float] | np.ndarray,
    cam: Camera,
    w: int,
    h: int,
) -> tuple[float, float, float] | None:
    """월드점 → (화면x, 화면y, 카메라깊이). 뒤쪽(Z<=0.05)이면 None."""
    right, up, forward = _basis(cam)
    d = np.asarray(point, dtype=float) - np.asarray(cam.pos, dtype=float)
    x, y, z = float(d @ right), float(d @ up), float(d @ forward)
    if z <= 0.05:
        return None
    f = (h / 2.0) / math.tan(math.radians(cam.fov) / 2.0)
    return (w / 2.0 + f * x / z, h / 2.0 - f * y / z, z)


# ------------------------------------------------------------------ 렌더
def render(s: Scene3D, w: int = 1280, h: int = 704) -> Image.Image:
    """블록아웃 PNG. 결정론적 — 같은 Scene3D는 항상 같은 바이트."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(C_SKY_TOP[i] + (C_SKY_BOT[i] - C_SKY_TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    draw = ImageDraw.Draw(img, "RGBA")

    # 바닥 + 원근 그리드 — 구도 힌트만 남기고 고주파 선은 최소화한다.
    # 2026-11-21 수정: 그리드가 img2img 잠재에 번져 실사 키프레임에 선이 남는 문제(라플라시안 893→757) 발견.
    # 간격을 넓히고 색을 배경에 가깝게 낮춰 "원근감만" 전달한다.
    horizon = project((0.0, 0.0, 200.0), s.camera, w, h)
    if horizon:
        draw.line([(0, horizon[1]), (w, horizon[1])], fill=C_HORIZON, width=1)
    for z in range(0, 34, 4):
        a, b = project((-12.0, 0.0, float(z)), s.camera, w, h), project((12.0, 0.0, float(z)), s.camera, w, h)
        if a and b:
            draw.line([(a[0], a[1]), (b[0], b[1])], fill=C_GRID, width=1)
    for x in range(-12, 13, 4):
        a, b = project((float(x), 0.0, 0.0), s.camera, w, h), project((float(x), 0.0, 32.0), s.camera, w, h)
        if a and b:
            draw.line([(a[0], a[1]), (b[0], b[1])], fill=C_GRID, width=1)

    # 배경 블록 — 먼 것부터 그려 앞의 것이 덮게 한다.
    for blk in sorted(s.blocks, key=lambda b: -b.pos[2]):
        cx, cy, cz = blk.pos
        sx, sy, sz = blk.size
        corners = [
            (cx - sx / 2, cy - sy / 2, cz - sz / 2), (cx + sx / 2, cy - sy / 2, cz - sz / 2),
            (cx + sx / 2, cy + sy / 2, cz - sz / 2), (cx - sx / 2, cy + sy / 2, cz - sz / 2),
            (cx - sx / 2, cy - sy / 2, cz + sz / 2), (cx + sx / 2, cy - sy / 2, cz + sz / 2),
            (cx + sx / 2, cy + sy / 2, cz + sz / 2), (cx - sx / 2, cy + sy / 2, cz + sz / 2),
        ]
        pts = [project(p, s.camera, w, h) for p in corners]
        if not all(pts):
            continue
        front = [pts[i] for i in (4, 5, 6, 7)]
        draw.polygon([(p[0], p[1]) for p in front], fill=blk.color + (200,))
        for i, j in ((4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            draw.line([(pts[i][0], pts[i][1]), (pts[j][0], pts[j][1])], fill=C_BLOCK_EDGE, width=1)

    # 인물 — 발/머리 투사 + 몸통 두께. heading은 색/원으로 구분.
    for fig in sorted(s.figures, key=lambda f: -f.pos[2]):
        x, _, z = fig.pos
        foot = project((x, 0.0, z), s.camera, w, h)
        head = project((x, fig.height, z), s.camera, w, h)
        if not (foot and head):
            continue
        thick = max(6, int(90.0 / head[2]))
        draw.line([(foot[0], foot[1]), (head[0], head[1])], fill=fig.color, width=thick)
        r = max(5, int(26.0 / head[2]))
        draw.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=C_HEAD)
        # heading은 색으로만 표현(C_FIGURE_BACK). 작은 원은 고주파라 제거함.

    # 상단 디버그 라벨 제거 — 이게 img2img 잠재에 번져 실사에 검은 띠로 남았다.
    # 구도 힌트는 features(메타/프롬프트)로 전달하고, 참조 이미지는 실루엣만 담는다.
    return img


# ------------------------------------------------------------------ 파일
def layout_path(project: project_mod.Project, scene_id: int) -> Path:
    return project.dir / "layouts" / f"layout_{int(scene_id):02d}.png"


def stage_key(project: project_mod.Project, scene: dict, sequence: int = 0) -> str:
    """레이아웃 캐시키. 대본 문구·인물/장소·순서가 바뀌면 다시 그린다."""
    s = build_scene(project, scene, sequence)
    return project_mod.digest(
        {
            "stage": "layout3d",
            "scene_id": s.scene_id,
            "camera": asdict(s.camera),
            "figures": [asdict(f) for f in s.figures],
            "blocks": [asdict(b) for b in s.blocks],
            "render_version": 2,  # 그리드/라벨 제거 반영 — 이전 캐시 무효화
        }
    )


def generate(
    project: project_mod.Project,
    scene: dict,
    *,
    sequence: int = 0,
    width: int = 1280,
    height: int = 704,
    force: bool = False,
) -> tuple[Path, dict]:
    """(경로, 메타). 캐시 있으면 재사용."""
    dest = layout_path(project, scene["id"])
    key = stage_key(project, scene, sequence)
    meta = {
        "file": dest.name, "key": key,
        "features": build_scene(project, scene, sequence).features,
    }
    if dest.exists() and not force:
        return dest, {**meta, "cached": True}
    img = render(build_scene(project, scene, sequence), width, height)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest, meta


def export_blender(s: Scene3D, dest: Path, width: int = 1280, height: int = 704) -> Path:
    """같은 Scene3D를 Blender headless 스크립트로 내보낸다(설치 시 선택적 사용).

    사용법(Blender 설치 후): blender -b -P <dest> -- --out <png>
    지금은 export만 하고 실행하지 않는다(Q9/설치 없음).
    """
    payload = json.dumps(asdict(s), ensure_ascii=False, indent=2)
    code = f'''"""D67 — Blender 백엔드 (자동 생성). 필요한 경우에만 실행."""
import bpy, json, math, sys
SCENE = json.loads(r"""{payload}""")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1.0)
    return m

# 바닥
bpy.ops.mesh.primitive_plane_add(size=60)
bpy.context.object.name = "ground"
bpy.context.object.data.materials.append(mat("ground", (0.18, 0.19, 0.23)))

# 배경 블록
for i, b in enumerate(SCENE["blocks"]):
    x, y, z = b["pos"]; sx, sy, sz = b["size"]
    bpy.ops.mesh.primitive_cube_add(location=(x, y, z))
    o = bpy.context.object; o.name = f"block_{{i:02d}}"; o.scale = (sx/2, sy/2, sz/2)
    o.data.materials.append(mat(f"block_{{i}}", tuple(c/255 for c in b["color"])))

# 인물 (간단한 capsule + 구)
for f in SCENE["figures"]:
    x, y, z = f["pos"]; h = f["height"]
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=h*0.75, location=(x, y+h*0.375, z))
    bpy.context.object.data.materials.append(mat("body", tuple(c/255 for c in f["color"])))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(x, y+h*0.9, z))
    bpy.context.object.data.materials.append(mat("head", (0.95, 0.8, 0.62)))

# 카메라
c = SCENE["camera"]; cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data); bpy.context.collection.objects.link(cam)
cam.location = c["pos"]; cam_data.lens = 50.0; bpy.context.scene.camera = cam
direction = [c["target"][i] - c["pos"][i] for i in range(3)]
cam.rotation_euler = __import__("mathutils").Vector(direction).to_track_quat("-Z", "Y").to_euler()

# 조명
bpy.ops.object.light_add(type="AREA", location=(0, 6, SCENE["camera"]["target"][2]))
bpy.context.object.data.energy = 800

s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE_NEXT"
s.render.resolution_x = {width}; s.render.resolution_y = {height}
s.render.filepath = (sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "layout_blender.png")
bpy.ops.render.render(write_still=True)
'''
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(code, encoding="utf-8")
    return dest
