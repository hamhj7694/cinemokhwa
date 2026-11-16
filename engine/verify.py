"""자동 품질 측정 — PRD §13.5 "수치 보조" 3종 + 키프레임 정합.

육안 체크리스트(8항목)를 대체하지 않는다. 사람이 볼 때 어디를 봐야 하는지
가리키는 용도다. 판정 등급:

  PASS  기준 충족
  WARN  기준 미달이지만 장면 의도로 설명 가능 (원경·뒷모습·보케)
  FAIL  실제 결함 가능성 (정지 화면, 노출 급변, 프레임 부족)

측정 함정(ENVIRONMENT §6): 전역 선명도는 의도된 심도 흐림을 "뭉개짐"으로
오판한다. 그래서 항상 **중앙 40%**만 본다. 그런데 피사체가 카메라에서
멀어지는 wide/behind 컷은 중앙 선명도가 구조적으로 떨어지므로 WARN으로 둔다.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from .config import Config
from .errors import CineError

CENTER_REGION = 0.4
SAMPLE_EVERY = 6          # 121프레임 → 21장 측정

# 판정 임계값
RATIO_PASS = 0.70         # 클립 중앙 선명도 >= 키프레임의 70%
YDIF_PASS = 1.0           # 프레임 간 평균 변화 (정지 화면이면 0에 가까움)
YAVG_STD_PASS = 5.0       # 컷 내 밝기 안정
MAE_PASS = 3.0            # 첫 프레임이 키프레임과 일치

WIDE_PATTERN = re.compile(
    r"\b(wide|long shot|extreme wide|establishing|from behind|behind her|"
    r"behind him|walks away|walks deeper|recedes|far away|back of)\b",
    re.IGNORECASE,
)

# 측정 등급 순서
_ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2}


# ------------------------------------------------------------------ plumbing
def _run(cmd: list[str], code: str, label: str) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise CineError(
            code,
            f"{label} 실패",
            hint="ffmpeg/ffprobe 경로와 입력 파일을 확인하세요.",
            detail=(proc.stderr or b"").decode("utf-8", "replace")[-1200:],
        )
    return proc.stdout


def probe_size(path: Path, cfg: Config) -> tuple[int, int]:
    out = _run(
        [
            str(cfg.ffprobe()), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        "FFMPEG-001",
        f"크기 확인 {path.name}",
    )
    text = out.decode("utf-8", "replace").strip()
    try:
        w, h = (int(v) for v in text.split(",")[:2])
    except ValueError as exc:
        raise CineError("FFMPEG-001", f"해상도를 읽지 못했습니다: {path.name}") from exc
    return w, h


def decode_gray(path: Path, cfg: Config) -> tuple[np.ndarray, int, int]:
    """영상 → (프레임, H, W) uint8. 디스크에 프레임을 남기지 않는다."""
    w, h = probe_size(path, cfg)
    raw = _run(
        [str(cfg.ffmpeg()), "-v", "error", "-i", str(path),
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        "FFMPEG-001",
        f"디코딩 {path.name}",
    )
    need = w * h
    if not raw or len(raw) % need:
        raise CineError(
            "RENDER-006",
            f"프레임 데이터가 손상되었습니다: {path.name}",
            detail=f"{len(raw)} bytes / frame {need}",
        )
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w), w, h


def _lap_var(patch: np.ndarray) -> float:
    """라플라시안 분산. patch는 [0,1] float."""
    q = np.pad(patch, 1, mode="edge")
    conv = (
        q[0:-2, 1:-1] + q[1:-1, 0:-2] - 4.0 * q[1:-1, 1:-1] + q[1:-1, 2:] + q[2:, 1:-1]
    )
    return float(conv.var()) * 65025.0


def _center(patch: np.ndarray) -> np.ndarray:
    h, w = patch.shape
    ch, cw = int(h * CENTER_REGION), int(w * CENTER_REGION)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return patch[y0:y0 + ch, x0:x0 + cw]


def is_wide_shot(scene: dict) -> bool:
    """대본이 원경·뒷모습 컷이면 선명도 기준을 WARN으로 완화한다."""
    return bool(WIDE_PATTERN.search(str(scene.get("visual", ""))))


# ------------------------------------------------------------------ measuring
def measure_clip(
    cfg: Config,
    clip: Path,
    keyframe: Path | None,
    scene: dict,
) -> dict:
    frames, w, h = decode_gray(clip, cfg)
    yavg = frames.reshape(len(frames), -1).mean(axis=1, dtype=np.float64)
    ydif = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2), dtype=np.float64)

    center_sharp = [
        _lap_var(_center(frames[i].astype(np.float32) / 255.0))
        for i in range(0, len(frames), SAMPLE_EVERY)
    ]

    key_center = None
    f0_mae = None
    if keyframe is not None and keyframe.exists():
        img = Image.open(keyframe).convert("L")
        if img.size != (w, h):
            img = img.resize((w, h), Image.LANCZOS)
        key_gray = np.asarray(img, dtype=np.float32)
        key_center = _lap_var(_center(key_gray / 255.0))
        f0_mae = float(np.abs(frames[0].astype(np.float32) - key_gray).mean())

    wide = is_wide_shot(scene)
    ratio = (
        float(np.mean(center_sharp)) / key_center
        if key_center and key_center > 0
        else None
    )

    return {
        "scene": int(scene.get("id", 0)),
        "file": clip.name,
        "frames": int(len(frames)),
        "size": [w, h],
        "wide_shot": wide,
        "yavg_mean": round(float(yavg.mean()), 2),
        "yavg_std": round(float(yavg.std()), 3),
        "yavg_drift": round(float(yavg[-1] - yavg[0]), 2),
        "ydif_min": round(float(ydif.min()), 3) if len(ydif) else 0.0,
        "ydif_median": round(float(np.median(ydif)), 3) if len(ydif) else 0.0,
        "center_sharpness": round(float(np.mean(center_sharp)), 1),
        "keyframe_center": round(key_center, 1) if key_center else None,
        "ratio": round(ratio, 3) if ratio else None,
        "first_frame_mae": round(f0_mae, 2) if f0_mae is not None else None,
    }


def judge(row: dict, expected_frames: int | None = None) -> dict[str, str]:
    """행 하나 → {항목: PASS|WARN|FAIL}."""
    wide = row["wide_shot"]
    out: dict[str, str] = {}

    if expected_frames is not None:
        out["프레임 수"] = "PASS" if row["frames"] >= expected_frames else "FAIL"

    ratio = row["ratio"]
    if ratio is None:
        out["중앙 선명도"] = "WARN"  # 키프레임 없음 → 비교 불가
    elif ratio >= RATIO_PASS:
        out["중앙 선명도"] = "PASS"
    else:
        out["중앙 선명도"] = "WARN" if wide else "FAIL"

    out["움직임(YDIF)"] = "PASS" if row["ydif_median"] >= YDIF_PASS else "FAIL"

    if row["yavg_std"] < YAVG_STD_PASS:
        out["밝기 안정"] = "PASS"
    elif wide and row["yavg_std"] < YAVG_STD_PASS * 3:
        out["밝기 안정"] = "WARN"
    else:
        out["밝기 안정"] = "FAIL"

    mae = row["first_frame_mae"]
    out["첫 프레임 정합"] = (
        "PASS" if mae is None or mae < MAE_PASS else "WARN"
    )
    return out


def overall(verdicts: dict[str, str]) -> str:
    level = max((_ORDER[v] for v in verdicts.values()), default=0)
    return {0: "PASS", 1: "WARN", 2: "FAIL"}[level]


# ------------------------------------------------------------------ reporting
def run(cfg: Config, project, *, sample_every_note: bool = True) -> dict:
    """run 단위 측정. clips/ 아래 실제 존재하는 클립만 본다."""
    scenes = {int(s["id"]): s for s in project.scenes()}
    rows: list[dict] = []
    for scene_id in sorted(scenes):
        clip = project.clip_path(scene_id)
        if not clip.exists():
            continue
        keyframe = project.keyframe_path(scene_id)
        expected = cfg.frames(float(scenes[scene_id].get("seconds", cfg.clip_seconds)))
        row = measure_clip(
            cfg,
            clip,
            keyframe if keyframe.exists() else None,
            scenes[scene_id],
        )
        row["verdicts"] = judge(row, expected)
        row["verdict"] = overall(row["verdicts"])
        rows.append(row)

    if not rows:
        raise CineError(
            "RENDER-007",
            "측정할 클립이 없습니다.",
            hint=f"3단계(클립)를 먼저 실행하세요: {project.dir}",
        )

    summary = {
        "run_id": project.run_id,
        "expected_frames": cfg.frames(cfg.clip_seconds),
        "sample_every": SAMPLE_EVERY,
        "clips": rows,
        "overall": overall(
            {f"{r['scene']}:{k}": v for r in rows for k, v in r["verdicts"].items()}
        ),
    }
    project.dir.joinpath("metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary["_path"] = str(project.dir / "metrics.json")
    return summary
