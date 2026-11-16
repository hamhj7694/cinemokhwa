"""FFmpeg — PNG 마스터 인코딩과 클립 이어붙이기(크로스페이드).

D57: 출력은 PNG 마스터 → libx264 CRF16 / yuv420p / faststart.
D53: 전환은 크로스페이드(기본 0.3초) 또는 하드컷. 완성 길이는
     sum(클립) - crossfade × (클립수 - 1) 이므로 타임라인에 그대로 기록한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import project as project_mod
from .config import Config
from .errors import CineError


def _run(cmd: list[str], code: str, label: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise CineError(
            code,
            f"{label} 실패 (ffmpeg 종료 코드 {proc.returncode})",
            hint="아래 상세의 마지막 줄을 확인하세요.",
            detail=(proc.stderr or "")[-2000:],
        )
    return proc


def probe_duration(path: Path, cfg: Config) -> float:
    proc = _run(
        [
            str(cfg.ffprobe()),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        "FFMPEG-001",
        f"길이 확인 {path.name}",
    )
    try:
        return float(proc.stdout.strip())
    except ValueError as e:
        raise CineError("FFMPEG-001", f"길이를 읽지 못했습니다: {path.name}") from e


def encode_frames(pattern: str, out: Path, cfg: Config) -> Path:
    """PNG 시퀀스 → mp4 (CRF16). `pattern`은 `%05d`를 포함해야 한다."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(cfg.ffmpeg()),
            "-y",
            "-framerate",
            str(cfg.fps),
            "-start_number",
            "1",
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-crf",
            str(cfg.crf),
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        "FFMPEG-002",
        f"프레임 인코딩 {out.name}",
    )
    return out


def concat(
    clips: list[Path],
    out: Path,
    cfg: Config,
    *,
    crossfade: float = 0.3,
) -> tuple[Path, list[float]]:
    """클립 N개 → 완성본 1개. 반환: (출력 경로, 클립별 길이)."""
    if not clips:
        raise CineError("FFMPEG-003", "이어붙일 클립이 없습니다.")
    durations = [probe_duration(c, cfg) for c in clips]
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(clips) == 1:
        shutil.copyfile(clips[0], out)
        return out, durations

    if crossfade <= 0:
        listfile = out.with_suffix(".concat.txt")
        listfile.write_text(
            "".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8"
        )
        _run(
            [
                str(cfg.ffmpeg()),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listfile),
                "-c",
                "copy",
                str(out),
            ],
            "FFMPEG-004",
            "하드컷 이어붙이기",
        )
        return out, durations

    shortest = min(durations)
    if crossfade >= shortest:
        raise CineError(
            "FFMPEG-005",
            f"크로스페이드({crossfade}초)가 가장 짧은 클립({shortest:.2f}초)보다 깁니다.",
            hint="전환 길이를 줄이거나 클립 길이를 늘리세요.",
        )

    cmd = [str(cfg.ffmpeg()), "-y"]
    for c in clips:
        cmd += ["-i", str(c)]

    filters: list[str] = []
    prev = "[0:v]"
    offset = durations[0] - crossfade
    for i in range(1, len(clips)):
        label = f"[v{i}]"
        filters.append(
            f"{prev}[{i}:v]xfade=transition=fade:duration={crossfade}"
            f":offset={offset:.3f}{label}"
        )
        prev = label
        offset += durations[i] - crossfade

    cmd += ["-filter_complex", ";".join(filters), "-map", prev]
    cmd += [
        "-r",
        str(cfg.fps),
        "-c:v",
        "libx264",
        "-crf",
        str(cfg.crf),
        "-preset",
        "slow",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    _run(cmd, "FFMPEG-006", "크로스페이드 이어붙이기")
    return out, durations


def write_timeline(
    project: project_mod.Project,
    clips: list[Path],
    durations: list[float],
    cfg: Config,
    *,
    crossfade: float,
) -> Path:
    scenes = project.scenes()
    entries = []
    cursor = 0.0
    for i, (clip, dur) in enumerate(zip(clips, durations)):
        scene = scenes[i] if i < len(scenes) else {"id": i + 1}
        entries.append(
            {
                "scene": scene.get("id", i + 1),
                "file": clip.name,
                "seconds": round(dur, 3),
                "start": round(cursor, 3),
                "narration": scene.get("narration", ""),
            }
        )
        cursor += dur - crossfade
    total = round(sum(durations) - crossfade * (len(clips) - 1), 3)
    timeline = {
        "run_id": project.run_id,
        "title": project.data.get("topic"),
        "mode": project.data.get("mode", "M-A"),
        "fps": cfg.fps,
        "size": [cfg.width, cfg.height],
        "crossfade": crossfade,
        "total_seconds": total,
        "scenes": entries,
    }
    project.timeline.write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return project.timeline
