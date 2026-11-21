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
assert abs(chosen["yavg"] - keyframe.TARGET_YAVG) <= 5, chosen
assert chosen["seed"] != 101, chosen
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

# 4) guided-40 scene 1 실측 재현 — 상대 비율(60%)로는 정상 밝기 후보가 탈락한다.
#    절대 하한이면 Y112/lap52 후보가 살아나 어두운 Y35 후보를 이긴다.
scene1 = [
    {"seed": 101, "center": 52.4, "yavg": 112.1},   # 정상 밝기 · 낮은 lap
    {"seed": 202, "center": 134.2, "yavg": 30.5},
    {"seed": 303, "center": 86.3, "yavg": 32.0},
    {"seed": 404, "center": 173.8, "yavg": 35.3},   # 구 로직이 뽑은 암부
]
assert keyframe.choose_candidate(scene1)["seed"] == 101
assert keyframe.MIN_CENTER_SHARPNESS == 40.0
print("PASS: D71b 절대 선명도 하한 — guided-40 암부 편향 재현 및 해소")

# 5) 씬 간 밝기 판정 임계값 — guided-40 실측 81.97은 FAIL, guided-20은 PASS
assert verify.CROSS_YAVG_WARN == 25.0 and verify.CROSS_YAVG_FAIL == 50.0
assert 81.97 > verify.CROSS_YAVG_FAIL
assert max([107.1, 112.78, 104.8]) - min([107.1, 112.78, 104.8]) < verify.CROSS_YAVG_WARN
print("PASS: D71 씬 간 밝기 WARN/FAIL 임계값")

print("\nALL PASS")
