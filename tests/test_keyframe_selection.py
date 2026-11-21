"""D71 키프레임 후보 선택 + 씬 간 밝기 검증 오프라인 테스트."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import keyframe, verify  # noqa: E402

# 1) 선명도만 보면 chose 어두운 시드 → D71은 밝기가 정상인 후보를 선택
cands = [
    {"seed": 101, "center": 900.0, "yavg": 34.0},   # 가장 선명하지만 암부
    {"seed": 202, "center": 700.0, "yavg": 108.0},  # 선명도 78% + 정상 밝기
    {"seed": 303, "center": 250.0, "yavg": 104.0},  # 밝기는 좋지만 흐림
    {"seed": 404, "center": 650.0, "yavg": 60.0},   # 중간
]
chosen = keyframe.choose_candidate(cands)
assert chosen["seed"] == 202, chosen
print("PASS: D71 암부 시드 대신 정상 밝기 시드 선택")

# 2) 선명도 풀 기준 — 전부 흐리면 그 안에서 밝기 기준 적용
dim = [
    {"seed": 1, "center": 100.0, "yavg": 30.0},
    {"seed": 2, "center": 90.0, "yavg": 103.0},
]
assert keyframe.choose_candidate(dim)["seed"] == 2
print("PASS: D71 전부 흐린 경우에도 밝기 기준 적용")

# 3) 밝기가 전부 정상이면 더 선명한 쪽(동률은 center 큰 쪽)
even = [
    {"seed": 1, "center": 800.0, "yavg": 105.0},
    {"seed": 2, "center": 900.0, "yavg": 105.0},
]
assert keyframe.choose_candidate(even)["seed"] == 2
print("PASS: D71 밝기 동률 시 선명도 우선")

# 4) 씬 간 밝기 판정 임계값 — guided-40 실측 81.97은 FAIL, guided-20은 PASS
assert verify.CROSS_YAVG_WARN == 25.0 and verify.CROSS_YAVG_FAIL == 50.0
assert 81.97 > verify.CROSS_YAVG_FAIL
assert max([107.1, 112.78, 104.8]) - min([107.1, 112.78, 104.8]) < verify.CROSS_YAVG_WARN
print("PASS: D71 씬 간 밝기 WARN/FAIL 임계값")

print("\nALL PASS")
