"""여러 run의 final.mp4에서 장면별 대표 프레임을 뽑아 한 장의 비교표로 만든다.

숫자 verify만으로 M2 게이트를 통과시키지 않기 위한 육안 판정 도구(D39/D47).
3씬 14.54초 기준 대표 시점(2.0s / 7.3s / 12.5s)을 사용한다.

사용법:
    python tools/contact_sheet.py --runs identity-01 guided-20 guided-40 guided-50
    python tools/contact_sheet.py --runs guided-40 guided-50 --out C:\\path\\compare.png

final.mp4가 아직 없는 run은 자동으로 건너뛴다.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(os.environ.get("CINEMOKHWA_ROOT", r"C:\Users\mbc\mokhwa"))
FFMPEG = Path(
    os.environ.get(
        "CINEMOKHWA_FFMPEG",
        r"C:\Users\mbc\mokhwa\tools\ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe",
    )
)
TIMES = [2.0, 7.3, 12.5]  # 3씬 대표 시점
CELL_W, CELL_H = 480, 264
LABEL_H = 22
GAP = 8


def extract(video: Path, second: float, dest: Path) -> None:
    if not FFMPEG.exists():
        raise FileNotFoundError(f"ffmpeg 없음: {FFMPEG}")
    cmd = [
        str(FFMPEG), "-v", "error", "-y",
        "-ss", str(second), "-i", str(video),
        "-frames:v", "1", "-vf", f"scale={CELL_W}:{CELL_H}", str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode or not dest.exists():
        raise RuntimeError(f"프레임 추출 실패({second}s): {r.stderr[-300:]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="run별 3씬 대표 프레임 비교표 생성")
    ap.add_argument("--runs", nargs="+", required=True, help="비교할 run id 목록")
    ap.add_argument("--out", type=Path, default=None, help="출력 PNG 경로")
    ap.add_argument("--times", nargs="+", type=float, default=TIMES, help="대표 시점(초)")
    args = ap.parse_args()

    available = []
    for run in args.runs:
        video = ROOT / "work" / run / "final.mp4"
        if video.exists():
            available.append((run, video))
        else:
            print(f"건너뜀: {run} — final.mp4 없음")

    if not available:
        print("비교할 영상이 없습니다.")
        return 1

    ncol = len(args.times)
    width = GAP + ncol * (CELL_W + GAP)
    height = GAP + len(available) * (CELL_H + LABEL_H + GAP)
    sheet = Image.new("RGB", (width, height), (24, 26, 32))
    draw = ImageDraw.Draw(sheet)

    with tempfile.TemporaryDirectory() as td:
        for row, (run, video) in enumerate(available):
            y = GAP + row * (CELL_H + LABEL_H + GAP)
            for col, second in enumerate(args.times):
                x = GAP + col * (CELL_W + GAP)
                frame_path = Path(td) / f"{run}_{col}.png"
                extract(video, second, frame_path)
                with Image.open(frame_path) as im:
                    sheet.paste(im.convert("RGB"), (x, y + LABEL_H))
                draw.text((x + 4, y + 4), f"{run}  scene {col + 1}  @{second:g}s",
                          fill=(235, 235, 240))

    out = args.out or (ROOT / "work" / f"contact_{'_'.join(args.runs)}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"비교표 저장: {out} ({sheet.size[0]}x{sheet.size[1]}, {len(available)}개 run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
