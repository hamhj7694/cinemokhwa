"""얼굴 정체성 유사도 측정 — OpenCV Zoo YuNet + SFace (Apache 2.0, CPU)

신규 파이프라인의 핵심 게이트. 기존 verify는 밝기·선명도만 봐서
"다른 사람처럼 보인다"는 사용자의 육안 불만을 잡지 못했다.
이 도구는 기준 카드와 생성물의 얼굴 임베딩 코사인 유사도를 직접 측정한다.

사용:
    python tools/face_identity.py --ref references/char_jun.png \
        --targets "keyframes/*.png" --json

모델(Apache 2.0, OpenCV Zoo):
    https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
    https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import sys
from pathlib import Path

import cv2
import numpy as np

DEFAULT_MODELS = Path(r"C:\Users\mbc\mokhwa\work\models\face")
YUNET = "face_detection_yunet_2023mar.onnx"
SFACE = "face_recognition_sface_2021dec.onnx"


def _detector(model_dir: Path, size: tuple[int, int]) -> "cv2.FaceDetectorYN":
    path = model_dir / YUNET
    if not path.exists():
        raise FileNotFoundError(f"YuNet 모델 없음: {path}")
    det = cv2.FaceDetectorYN_create(str(path), "", size,
                                    score_threshold=0.6, nms_threshold=0.3,
                                    top_k=5000)
    return det


def _recognizer(model_dir: Path) -> "cv2.FaceRecognizerSF":
    path = model_dir / SFACE
    if not path.exists():
        raise FileNotFoundError(f"SFace 모델 없음: {path}")
    return cv2.FaceRecognizerSF_create(str(path), "")


def face_feature(img: np.ndarray, det: "cv2.FaceDetectorYN",
                 rec: "cv2.FaceRecognizerSF") -> np.ndarray | None:
    """이미지에서 가장 큰 얼굴 1개의 임베딩. 얼굴 없으면 None."""
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    # faces: [x, y, w, h, 5개 랜드마크 x2, score]
    face = max(faces, key=lambda f: f[2] * f[3])
    aligned = rec.alignCrop(img, face)
    return rec.feature(aligned)


def load(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"이미지 읽기 실패: {path}")
    return img


def measure(ref: Path, targets: list[Path], model_dir: Path) -> list[dict]:
    rec = _recognizer(model_dir)
    ref_img = load(ref)
    det = _detector(model_dir, (ref_img.shape[1], ref_img.shape[0]))
    ref_feat = face_feature(ref_img, det, rec)
    if ref_feat is None:
        raise ValueError(f"기준 이미지에서 얼굴을 찾지 못함: {ref}")

    rows: list[dict] = []
    for path in targets:
        img = load(path)
        det = _detector(model_dir, (img.shape[1], img.shape[0]))
        feat = face_feature(img, det, rec)
        if feat is None:
            rows.append({"file": path.name, "face": False, "similarity": None})
            continue
        sim = float(rec.match(ref_feat, feat, cv2.FaceRecognizerSF_FR_COSINE))
        rows.append({"file": path.name, "face": True, "similarity": round(sim, 4)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", type=Path, required=True, help="기준 얼굴 이미지")
    ap.add_argument("--targets", required=True, help="비교할 이미지 glob (따옴표 필수)")
    ap.add_argument("--models", type=Path, default=DEFAULT_MODELS, help="ONNX 모델 폴더")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = ap.parse_args()

    targets = sorted(Path(p) for p in globmod.glob(args.targets))
    if not targets:
        print(f"대상 없음: {args.targets}", file=sys.stderr)
        return 2

    rows = measure(args.ref, targets, args.models)
    if args.json:
        print(json.dumps({"ref": str(args.ref), "rows": rows},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"기준: {args.ref}")
    print(f"{'file':<28} {'face':>5} {'sim':>8}")
    print("-" * 44)
    for r in rows:
        sim = "-" if r["similarity"] is None else f"{r['similarity']:.4f}"
        print(f"{r['file']:<28} {str(r['face']):>5} {sim:>8}")
    sims = [r["similarity"] for r in rows if r["similarity"] is not None]
    if sims:
        print("-" * 44)
        print(f"평균 {np.mean(sims):.4f}  최소 {np.min(sims):.4f}  최대 {np.max(sims):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
