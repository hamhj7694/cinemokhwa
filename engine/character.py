"""D66 ① — 인물별 정면 기준 이미지(캐릭터 카드).

컷 장면의 IPAdapter 참조로 "가장 가까운 앞 장면 키프레임"을 쓰면 그 장면이
뒷모습·원경일 때 얼굴 정보가 없어 인물이 바뀐다(2026-11-17 육안 FAIL).
여기서는 bible의 각 인물을 **정면·중립 표정·균일 조명**으로 한 장 만들어
`work/<run>/references/char_<id>.png`에 두고, 모든 컷이 그 카드를 참조하게 한다.

카드 생성 자체는 키프레임과 같은 SDXL 워크플로(4시드 → 중앙 선명도 최고)를
재사용한다. 새 모델·유료 API는 쓰지 않는다(D39/D47).
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from . import keyframe, project as project_mod
from .comfy import Comfy
from .config import Config
from .script import KEYFRAME_NEGATIVE, STYLES

# 정면을 강제하는 프롬프트 조각. 뒷모습/옆모습을 네거티브로도 막는다.
FRONTAL_SUFFIX = (
    "front-facing portrait, looking directly at camera, neutral expression, "
    "centered head and shoulders, even soft frontal lighting, plain neutral background"
)
CARD_NEGATIVE = (
    KEYFRAME_NEGATIVE
    + ", side view, profile, back view, turned away, looking away, "
    "face obscured, facing away"
)


def card_path(project: project_mod.Project, char_id: str) -> Path:
    """인물 id → 기준 이미지 경로."""
    return project.dir / "references" / f"char_{str(char_id).strip().lower()}.png"


def card_for(project: project_mod.Project, scene: dict) -> tuple[Path, str] | None:
    """장면에 나오는 인물 중 **카드가 실제로 있는** 첫 인물을 돌려준다.

    `bible.characters[].ref`(상대 경로)가 있으면 그걸 우선 쓰고, 없으면
    규칙 경로(`references/char_<id>.png`)를 쓴다(구버전 대본 호환).
    """
    bible = project.bible()
    by_id = {
        str(c.get("id", "")).strip().lower(): c
        for c in (bible.get("characters") or [])
        if isinstance(c, dict)
    }
    for anchor in scene.get("anchors") or []:
        text = str(anchor).strip()
        if not text.startswith("char:"):
            continue
        cid = text[5:].strip().lower()
        entry = by_id.get(cid) or {}
        ref = str(entry.get("ref") or "").strip()
        path = project.dir / ref if ref else card_path(project, cid)
        if path.exists():
            return path, f"char:{cid}"
    return None


def card_by_label(project: project_mod.Project, label: str) -> Path | None:
    """캐시에 저장된 라벨(`char:jun`)로 경로를 다시 찾는다."""
    if not str(label).startswith("char:"):
        return None
    found, _ = card_for(project, {"anchors": [label]})
    return found


def prompt_for(project: project_mod.Project, char: dict) -> str:
    style = STYLES.get(project.style, STYLES["cinematic"])["suffix"]
    desc = str(char.get("desc") or "").strip()
    return f"{desc}, {FRONTAL_SUFFIX}, {style}"


def stage_key(cfg: Config, project: project_mod.Project) -> str:
    """카드 캐시키. 인물 설명·화풍·모델·크기가 바뀌면 다시 만든다."""
    chars = project.bible().get("characters") or []
    return project_mod.digest(
        {
            "stage": "characters",
            "chars": [
                {"id": str(c.get("id") or ""), "desc": str(c.get("desc") or "")}
                for c in chars
                if isinstance(c, dict)
            ],
            "style": project.style,
            "ckpt": cfg.sdxl_ckpt,
            "steps": cfg.keyframe_steps,
            "size": [cfg.width, cfg.height],
            "seeds": keyframe.SEEDS,
        }
    )


def _write_refs(project: project_mod.Project, paths: dict[str, Path]) -> None:
    """대본 bible에 `ref`(상대 경로)를 적어 D66 ①을 파일로도 보이게 한다."""
    if not project.script_path.exists() or not paths:
        return
    raw = json.loads(project.script_path.read_text(encoding="utf-8"))
    bible = raw.get("bible") or {}
    changed = False
    for char in bible.get("characters") or []:
        cid = str(char.get("id") or "").strip().lower()
        path = paths.get(cid)
        if path is None:
            continue
        ref = path.relative_to(project.dir).as_posix()
        if char.get("ref") != ref:
            char["ref"] = ref
            changed = True
    if changed:
        project.script_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def generate_all(
    cfg: Config,
    comfy: Comfy,
    project: project_mod.Project,
    *,
    force: bool = False,
) -> list[dict]:
    """bible의 모든 인물 카드를 생성(또는 캐시). 메타 리스트를 돌려준다."""
    chars = [
        c for c in (project.bible().get("characters") or []) if isinstance(c, dict)
    ]
    if not chars:
        return []

    t0 = time.time()
    meta: list[dict] = []
    made: dict[str, Path] = {}
    for char in chars:
        cid = str(char.get("id") or "").strip().lower()
        if not cid:
            continue
        dest = card_path(project, cid)
        if dest.exists() and not force:
            made[cid] = dest  # 캐시여도 bible의 ref는 다시 적는다(대본 재생성 대비)
            meta.append({"char": cid, "file": dest.name, "cached": True})
            continue

        prompt = prompt_for(project, char)
        best: tuple[Path, int, float] | None = None
        candidates: list[dict] = []
        for seed in keyframe.SEEDS:
            prefix = f"cinemokhwa/{project.run_id}/char_{cid}_s{seed}"
            workflow = keyframe.build_workflow(
                cfg, prompt, CARD_NEGATIVE, seed, prefix
            )
            record = comfy.run(workflow, f"캐릭터 카드 {cid} s{seed}", timeout_s=900)
            files = comfy.materialize(record, project.dir / "tmp")
            if not files:
                from .errors import CineError

                raise CineError(
                    "RENDER-003", f"캐릭터 카드 산출물이 없습니다: {cid} (시드 {seed})"
                )
            full, center = keyframe._laplacian_var(files[0])
            candidates.append({"seed": seed, "center": round(center, 1)})
            if best is None or center > best[2]:
                best = (files[0], seed, center)

        assert best is not None
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(best[0], dest)
        made[cid] = dest
        meta.append(
            {
                "char": cid,
                "file": dest.name,
                "seed": best[1],
                "center_sharpness": round(best[2], 1),
                "candidates": candidates,
                "elapsed": round(time.time() - t0, 1),
            }
        )

    _write_refs(project, made)
    return meta
