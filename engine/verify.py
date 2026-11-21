"""자동 품질 측정 — PRD §13.5 "수치 보조" + 경계 구분(P1-16).

육안 체크리스트(8항목)를 대체하지 않는다. 사람이 볼 때 어디를 봐야 하는지
가리키는 용도다. 판정 등급:

  PASS  기준 충족
  WARN  기준 미달이지만 장면 의도로 설명 가능 (원경·뒷모습·보케·움직임)
  FAIL  실제 결함 가능성 (정지 화면, 노출 급변, 이음새 어긋남)

P1-16 변경(2026-11-17): 예전엔 모든 장면의 첫 프레임을 **자기 키프레임**과
비교했다. 같은 `shot`의 연장 장면은 시작이 앞 클립의 마지막 프레임이므로
이게 오판이었다(MAE 40.19 → FAIL). 이제 `timeline`의 `shot`으로 컷/연장을
나눠 연장은 **앞 클립 마지막 PNG**를 기준으로 본다. 컷은 자기 키프레임에
SSIM·팔레트를 더해 "구도가 달라도 인물·색감이 유지되는지"를 본다.

측정 함정(ENVIRONMENT §6): 전역 선명도는 의도된 심도 흐림을 "뭉개짐"으로
오판한다. 그래서 항상 **중앙 40%**만 본다.
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
RATIO_PASS = 0.70         # 클립 중앙 선명도 >= 참조의 70%
YDIF_PASS = 1.0           # 프레임 간 평균 변화 (정지 화면이면 0에 가까움)
YAVG_STD_PASS = 5.0       # 컷 내 밝기 안정
MAE_PASS = 3.0            # 연장 이음새가 앞 클립 끝과 일치
SSIM_PASS = 0.30          # 컷 첫 프레임 ↔ 키프레임 구조 유사도
SSIM_WARN = 0.15
PALETTE_PASS = 30.0       # 팔레트(8단계 RGB 히스토그램) L1 거리, 0~100
PALETTE_WARN = 50.0
DRIFT_WARN = 30.0         # 클립 첫↔끝 프레임 차이(움직임에 따른 자연 변화)

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


def decode_first_rgb(path: Path, cfg: Config) -> np.ndarray:
    """영상 첫 프레임 → (H, W, 3) uint8. 팔레트 비교용."""
    w, h = probe_size(path, cfg)
    raw = _run(
        [str(cfg.ffmpeg()), "-v", "error", "-i", str(path), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        "FFMPEG-001",
        f"첫 프레임 디코딩 {path.name}",
    )
    if len(raw) != w * h * 3:
        raise CineError("RENDER-006", f"첫 프레임 데이터가 손상되었습니다: {path.name}")
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)


def _rgb(path: Path, w: int, h: int) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


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


def _ssim(a: np.ndarray, b: np.ndarray) -> float:
    """8×8 블록 평균 구조적 유사도. a,b는 uint8 grayscale, 같은 크기."""
    x, y = a.astype(np.float64), b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    h, w = x.shape
    bh, bw = max(8, h // 8), max(8, w // 8)
    vals: list[float] = []
    for i in range(0, h, bh):
        for j in range(0, w, bw):
            xa, ya = x[i:i + bh, j:j + bw], y[i:i + bh, j:j + bw]
            if xa.size < 16:
                continue
            mx, my = xa.mean(), ya.mean()
            vx, vy = xa.var(), ya.var()
            cov = ((xa - mx) * (ya - my)).mean()
            num = (2 * mx * my + c1) * (2 * cov + c2)
            den = (mx * mx + my * my + c1) * (vx + vy + c2)
            vals.append(float(num / den) if den else 1.0)
    return float(np.mean(vals)) if vals else 0.0


def _palette(a: np.ndarray, b: np.ndarray) -> float:
    """8단계/channel RGB 히스토그램 L1 거리(0~100, 낮을수록 같다)."""
    bins = [(0, 256)] * 3
    ha = np.histogramdd(a.reshape(-1, 3), bins=8, range=bins)[0].ravel().astype(float)
    hb = np.histogramdd(b.reshape(-1, 3), bins=8, range=bins)[0].ravel().astype(float)
    ha /= max(ha.sum(), 1.0)
    hb /= max(hb.sum(), 1.0)
    return round(float(0.5 * np.abs(ha - hb).sum() * 100), 1)


def is_wide_shot(scene: dict) -> bool:
    """대본이 원경·뒷모습 컷이면 선명도 기준을 WARN으로 완화한다."""
    return bool(WIDE_PATTERN.search(str(scene.get("visual", ""))))


def chain_sources(project) -> dict[int, int | None]:
    """같은 shot의 앞 장면 id. D63 — verify가 컷/연장을 구분하는 근거."""
    previous: dict[int, int | None] = {}
    by_shot: dict[str, int] = {}
    for s in project.scenes():
        sid = int(s["id"])
        shot = str(s.get("shot") or f"S{sid}")
        previous[sid] = by_shot.get(shot)
        by_shot[shot] = sid
    return previous


def last_frame_path(project, scene_id: int) -> Path | None:
    """그 클립의 마지막 PNG. 연장 장면의 비교 기준(D65)."""
    files = sorted((project.frames / f"scene_{int(scene_id):02d}").glob("*.png"))
    return files[-1] if files else None


# ------------------------------------------------------------------ measuring
def measure_clip(
    cfg: Config,
    clip: Path,
    reference: Path | None,
    scene: dict,
    *,
    boundary: str = "open",
    ref_label: str = "",
) -> dict:
    frames, w, h = decode_gray(clip, cfg)
    yavg = frames.reshape(len(frames), -1).mean(axis=1, dtype=np.float64)
    ydif = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2), dtype=np.float64)

    center_sharp = [
        _lap_var(_center(frames[i].astype(np.float32) / 255.0))
        for i in range(0, len(frames), SAMPLE_EVERY)
    ]

    ref_center = None
    f0_mae = None
    ssim = None
    palette = None
    if reference is not None and reference.exists():
        img = Image.open(reference).convert("L")
        if img.size != (w, h):
            img = img.resize((w, h), Image.LANCZOS)
        ref_gray = np.asarray(img, dtype=np.float32)
        ref_center = _lap_var(_center(ref_gray / 255.0))
        f0_mae = float(np.abs(frames[0].astype(np.float32) - ref_gray).mean())
        ssim = _ssim(frames[0].astype(np.uint8), ref_gray.astype(np.uint8))
        palette = _palette(decode_first_rgb(clip, cfg), _rgb(reference, w, h))

    wide = is_wide_shot(scene)
    ratio = (
        float(np.mean(center_sharp)) / ref_center
        if ref_center and ref_center > 0
        else None
    )
    drift = float(np.abs(frames[-1].astype(np.float32) - frames[0]).mean())

    return {
        "scene": int(scene.get("id", 0)),
        "file": clip.name,
        "frames": int(len(frames)),
        "size": [w, h],
        "boundary": boundary,          # "open"(컷) | "extend"(같은 shot 연장)
        "reference": ref_label,        # keyframeNN | prevNN
        "wide_shot": wide,
        "yavg_mean": round(float(yavg.mean()), 2),
        "yavg_std": round(float(yavg.std()), 3),
        "yavg_drift": round(float(yavg[-1] - yavg[0]), 2),
        "ydif_min": round(float(ydif.min()), 3) if len(ydif) else 0.0,
        "ydif_median": round(float(np.median(ydif)), 3) if len(ydif) else 0.0,
        "center_sharpness": round(float(np.mean(center_sharp)), 1),
        "keyframe_center": round(ref_center, 1) if ref_center else None,
        "ratio": round(ratio, 3) if ratio else None,
        "first_frame_mae": round(f0_mae, 2) if f0_mae is not None else None,
        "ssim": round(ssim, 3) if ssim is not None else None,
        "palette_l1": palette,
        "end_drift": round(drift, 2),
    }


def judge(row: dict, expected_frames: int | None = None) -> dict[str, str]:
    """행 하나 → {항목: PASS|WARN|FAIL}."""
    wide = row["wide_shot"]
    out: dict[str, str] = {}

    if expected_frames is not None:
        out["프레임 수"] = "PASS" if row["frames"] >= expected_frames else "FAIL"

    ratio = row["ratio"]
    if ratio is None:
        out["중앙 선명도"] = "WARN"  # 참조 없음 → 비교 불가
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

    # 경계별 기준(P1-16)
    if row["boundary"] == "extend":
        mae = row["first_frame_mae"]
        out["이음새 정합"] = (
            "PASS" if mae is not None and mae < MAE_PASS else "FAIL"
        )
    else:
        ssim, palette = row["ssim"], row["palette_l1"]
        if ssim is None or palette is None:
            out["컷 참조 정합"] = "WARN"
        elif ssim >= SSIM_PASS and palette <= PALETTE_PASS:
            out["컷 참조 정합"] = "PASS"
        elif ssim >= SSIM_WARN and palette <= PALETTE_WARN:
            out["컷 참조 정합"] = "WARN"
        else:
            out["컷 참조 정합"] = "FAIL"

    drift = row["end_drift"]
    out["클립 드리프트"] = "PASS" if drift is not None and drift < DRIFT_WARN else "WARN"
    return out


def overall(verdicts: dict[str, str]) -> str:
    level = max((_ORDER[v] for v in verdicts.values()), default=0)
    return {0: "PASS", 1: "WARN", 2: "FAIL"}[level]


# ------------------------------------------------------------------ reporting
def run(cfg: Config, project, *, sample_every_note: bool = True) -> dict:
    """run 단위 측정. clips/ 아래 실제 존재하는 클립만 본다."""
    scenes = {int(s["id"]): s for s in project.scenes()}
    chain_of = chain_sources(project)
    rows: list[dict] = []
    for scene_id in sorted(scenes):
        clip = project.clip_path(scene_id)
        if not clip.exists():
            continue

        # 연장은 자기 키프레임이 아니라 **앞 클립 마지막 프레임**이 기준이다.
        prev = chain_of.get(scene_id)
        boundary = "extend" if prev is not None else "open"
        reference = project.keyframe_path(scene_id)
        ref_label = f"keyframe{scene_id:02d}"
        if prev is not None:
            last = last_frame_path(project, prev)
            if last is not None:
                reference, ref_label = last, f"prev{prev:02d}"
        if not reference.exists():
            reference = None

        expected = cfg.frames(float(scenes[scene_id].get("seconds", cfg.clip_seconds)))
        row = measure_clip(
            cfg,
            clip,
            reference,
            scenes[scene_id],
            boundary=boundary,
            ref_label=ref_label,
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
