"""run 단위 캐시·재개.

`work/<run_id>/` 아래에 단계별 산출물과 `state.json`을 둔다.
단계 완료 여부는 (상태=done) AND (입력 해시 일치)일 때만 참으로 본다.
따라서 프롬프트·시드·설정이 바뀌면 그 단계만 자동으로 다시 돈다(FR-17).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import CineError

STAGES = ("script", "keyframes", "clips", "assemble")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def digest(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def file_digest(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


@dataclass
class Project:
    dir: Path
    data: dict
    state: dict

    # ------------------------------------------------------------- paths
    @property
    def run_id(self) -> str:
        return self.data["run_id"]

    @property
    def script_path(self) -> Path:
        return self.dir / "script.json"

    @property
    def keyframes(self) -> Path:
        return self.dir / "keyframes"

    @property
    def clips(self) -> Path:
        return self.dir / "clips"

    @property
    def frames(self) -> Path:
        return self.dir / "frames"

    @property
    def final(self) -> Path:
        return self.dir / "final.mp4"

    @property
    def timeline(self) -> Path:
        return self.dir / "timeline.json"

    @property
    def log(self) -> Path:
        return self.dir / "run.log"

    @property
    def target_seconds(self) -> float:
        return float(self.data["target_seconds"])

    @property
    def style(self) -> str:
        return str(self.data.get("style", "cinematic"))

    # ------------------------------------------------------------- scenes
    def scenes(self) -> list[dict]:
        if not self.script_path.exists():
            return []
        return json.loads(self.script_path.read_text(encoding="utf-8"))["scenes"]

    def bible(self) -> dict:
        """연속성 앵커(인물·장소·조명). 구버전 script.json이면 빈 값."""
        if not self.script_path.exists():
            return {"characters": [], "places": [], "look": ""}
        raw = json.loads(self.script_path.read_text(encoding="utf-8"))
        bible = raw.get("bible")
        if not isinstance(bible, dict):
            return {"characters": [], "places": [], "look": ""}
        return {
            "characters": bible.get("characters") or [],
            "places": bible.get("places") or [],
            "look": str(bible.get("look") or ""),
        }

    def scene(self, scene_id: int) -> dict:
        for s in self.scenes():
            if int(s["id"]) == int(scene_id):
                return s
        raise CineError("PROJECT-003", f"장면 {scene_id}이(가) 대본에 없습니다.")

    def keyframe_path(self, scene_id: int) -> Path:
        return self.keyframes / f"scene_{int(scene_id):02d}.png"

    def clip_path(self, scene_id: int) -> Path:
        return self.clips / f"scene_{int(scene_id):02d}.mp4"

    # ------------------------------------------------------------- stages
    def done(self, stage: str, key: str) -> bool:
        rec = self.state.get("stages", {}).get(stage) or {}
        return rec.get("status") == "done" and rec.get("key") == key

    def begin(self, stage: str, key: str) -> None:
        self.state.setdefault("stages", {})[stage] = {
            "status": "running",
            "key": key,
            "started": now(),
        }
        self.save()

    def finish(self, stage: str, key: str, **extra) -> None:
        rec = self.state.setdefault("stages", {})[stage]
        rec.update({"status": "done", "key": key, "finished": now(), **extra})
        self.save()

    def fail(self, stage: str, message: str) -> None:
        rec = self.state.setdefault("stages", {}).setdefault(stage, {})
        rec.update({"status": "failed", "error": message, "finished": now()})
        self.save()

    def save(self) -> None:
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.dir / "state.json")

    def log_line(self, text: str) -> None:
        with self.log.open("a", encoding="utf-8") as f:
            f.write(f"{now()} {text}\n")


def create(
    work_root: Path,
    topic: str,
    target_seconds: float,
    *,
    style: str = "cinematic",
    run_id: str | None = None,
    notes: str = "",
    params: dict | None = None,
) -> Project:
    run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
    d = work_root / run_id
    if (d / "project.json").exists():
        raise CineError(
            "PROJECT-001",
            f"이미 존재하는 실행입니다: {run_id}",
            hint="이어서 하려면 --run-id, 새로 만들려면 다른 run_id를 쓰세요.",
        )
    for sub in ("keyframes", "clips", "frames"):
        (d / sub).mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": run_id,
        "topic": topic,
        "target_seconds": float(target_seconds),
        "style": style,
        "mode": "M-A",
        "input_mode": "auto",
        "created": now(),
        "notes": notes,
        "params": params or {},
    }
    (d / "project.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    project = Project(dir=d, data=data, state={"run_id": run_id, "stages": {}})
    project.save()
    return project


def load(work_root: Path, run_id: str) -> Project:
    d = work_root / run_id
    data_path = d / "project.json"
    if not data_path.exists():
        runs = [p.name for p in sorted(work_root.glob("*")) if (p / "project.json").exists()]
        hint = "사용 가능한 실행: " + (", ".join(runs[-5:]) if runs else "없음")
        raise CineError("PROJECT-002", f"실행을 찾을 수 없습니다: {run_id}", hint=hint)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    state_path = d / "state.json"
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {"run_id": run_id, "stages": {}}
    )
    return Project(dir=d, data=data, state=state)


def list_runs(work_root: Path) -> list[dict]:
    rows: list[dict] = []
    if not work_root.exists():
        return rows
    for d in sorted(work_root.iterdir()):
        if not (d / "project.json").exists():
            continue
        data = json.loads((d / "project.json").read_text(encoding="utf-8"))
        state_path = d / "state.json"
        state = (
            json.loads(state_path.read_text(encoding="utf-8"))
            if state_path.exists()
            else {"stages": {}}
        )
        stages = {k: v.get("status", "?") for k, v in (state.get("stages") or {}).items()}
        rows.append(
            {
                "run_id": d.name,
                "topic": data.get("topic", ""),
                "target_seconds": data.get("target_seconds"),
                "final": (d / "final.mp4").exists(),
                "stages": stages,
            }
        )
    return rows


def reset(project: Project, stages: list[str] | None = None) -> list[str]:
    """지정 단계의 산출물 삭제. 반환값은 실제로 지운 항목."""
    removed: list[str] = []
    targets = stages or list(STAGES)
    for stage in targets:
        if stage == "script" and project.script_path.exists():
            project.script_path.unlink()
            removed.append(str(project.script_path))
        elif stage == "keyframes" and project.keyframes.exists():
            for p in project.keyframes.glob("*.png"):
                p.unlink()
                removed.append(str(p))
        elif stage == "clips" and project.clips.exists():
            for p in project.clips.glob("*.mp4"):
                p.unlink()
                removed.append(str(p))
            if project.frames.exists():
                shutil.rmtree(project.frames, ignore_errors=True)
                removed.append(str(project.frames))
        elif stage == "assemble":
            for p in (project.final, project.timeline):
                if p.exists():
                    p.unlink()
                    removed.append(str(p))
        project.state.setdefault("stages", {}).pop(stage, None)
    project.save()
    return removed
