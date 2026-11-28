# P2 프리비즈 정밀도 × 가이드 채널 실험 계획

> 2026-11-28 · 실험 **설계 완료 / 실행 미착수**.
> 모든 수치는 앞으로 측정할 값. 이 문서 자체가 결과가 아니다.
> 관련: [Adaptive Previs](../design/ADAPTIVE_PREVIS.md), [P2_TEST_PLAN](../P2_TEST_PLAN.md), [H-021/H-022](../P2_ROADMAP.md).

## 실험 질문

1. `coarse`가 `joint_lite`보다 **역동적 동작의 자연스러움**을 개선하는가?
2. `joint_lite`가 **접촉·손동작의 정확도**를 개선하는가? 관절을 추가해도 부작용은 없는가?
3. **3D proxy가 실사 결과에 보이는 현상(형상·채도 전이)**은 geometry 때문인가, RGB guide 채널 때문인가?
4. 어떤 조건에서 프리비즈가 **가이드 없음보다 불리**한가?
5. LTX-2.5 12GB 로컬에서 이미지 핀 방식과 공식 IC-LoRA 방식이 **실제로 실행 가능**한가?

## 실험 케이스

| Case | 샷/장면 (3~5초, 24fps) | 비교할 항목 | 기대·가설 |
|---|---|---|---|
| E1 | **추격/달리기**: 한 명이 좌→우, 카메라 tracking. 접촉 없음 | `none`, `coarse`, `joint_lite` | coarse에서 위치/카메라 유지 + 덜 경직된 팔다리 표현 가능성 |
| E2 | **손목 잡기/물건 잡기**: 사람+명시적 소품, 접촉 시점 t=2s | `coarse` vs `joint_lite` | joint_lite의 접촉 정확도 개선 가능성 |
| E3 | **표정 클로즈업**: 상체 정지, 고개/시선만 이동 | `none`, `coarse`, `joint_lite` | 관절/형상 상세가 얼굴 품질을 자동 개선하지 않음 |
| E4 | **카메라 통제**: 객체는 정지, 카메라 dolly/pan | `none`, `coarse` | 3D 카메라 경로 제어 효과 |
| E5 (후속) | 완성 3D 물체 재렌더/제품 회전 | `coarse`, `geometry_rerender` | full geometry가 도움이 되는 별도 용례 |

E1/E2/E3/E4에 각각 `camera/root_path/contact_timeline`의 정답 트랙을 미리 기록. E2에서 최초 손목/소품 접촉 시각·좌표 누락 시 평가 불가. 3D 생성이 정확해도 AI 영상이 다르게 나오면 별개로 처리.

## 실험 조건과 재현성

**고정:** RTX 3060 12GB(기존 P2 환경), 모델/checkpoint 해시, 24fps, 해상도, 프롬프트의 참조 외형, 첫 실사 키프레임, seed, frame count, ComfyUI/노드 버전, 출력 경로. 같은 실험군에서 **변경 변수 한 번에 하나**.

**분리할 축:**
- `previs_profile`: none / coarse / joint_lite / geometry_rerender(후속).
- `guide_channel`: prompt_only / sparse_rgb_anchors / layout_video_ic_lora / motion_track_ic_lora(가용성 확인 후).
- `guide_strength`, frame indices, 첫 프레임, 시드 별도 기록. **형상 프로필과 가이드 채널을 동시에 바꾸지 않는다.**

### 실행 순서(비용 절약)
1. **G0 — 문서/계약:** mock fixture에 policy 필드·반례 생성, Blender 렌더 정합성 테스트. GPU 생성 0회.
2. **G1 — 3D/정적 준비:** E1-E4 샷별 coarse/joint_lite 프리비즈 CPU/Blender 렌더, bbox/camera/root/contact JSON 및 clean guide와 debug guide 분리. PNG 프레임 자체를 영상 모델에 보내기 전에 정상 시퀀스인지 시각 확인.
3. **G2 — 기존 `LTXVAddGuide` 경로 유효성:** 같은 seed/첫 실사 이미지로 E1 **prompt_only vs coarse sparse anchors**를 먼저 한 쌍만 생성. 모델의 실제 guide 적용 위치·중복 및 GPU 소요 로그 확보. 효과 없다면 계속 생성하지 않고 원인 진단.
4. **G3 — 프리비즈 수준 비교:** guide 채널을 **G2에서 검증된 한 가지**로 고정한 뒤 E1 coarse/joint_lite, E2 coarse/joint_lite, E3 none/coarse/joint_lite 비교. 25f 스모크는 노드/메모리 확인만, **3~5초 행동 품질은 3~5초 실영상에서만** 판정.
5. **G4 — 필요할 때만 전용 IC-LoRA 채널:** 다운로드 허용 여부/라이선스/양자화 호환/VRAM 측정 후, 같은 E1에서 sparse anchors vs layout_video_ic_lora 또는 motion_track_ic_lora 비교. 준비가 안 되면 `blocked`로 기록하고 우회 성공 선언 금지.
6. **G5 — 재현성:** 초기 우세 조건은 서로 다른 시드 **최소 2회 추가 검증**을 목표로 한다. 1시드 육안만으로 일반화하지 않는다.

**비용 주의:** 기존 LTX-2.5 Q3 960×544 25프레임 단독 스모크는 530.5초. 5초가 42.8분이라는 숫자는 **선형 추정일 뿐**, guide/IC-LoRA 사용 시 실측 아님. 조건별 GPU 사용은 직렬화. 모델 실측 비용 및 한 번에 허용할 실험 개수는 A0가 시험마다 통제.

## 측정 기준 (사전 정의; 미확정 목표는 실험 가설)

| 지표 | 측정 및 기록 방식 | 실패/특이값 |
|---|---|---|
| Root/객체 경로 오차 | Blender ground-truth bbox 중심/크기/방향 vs 영상에서 수동/모델 추출한 궤적 | 미검출은 `not_measurable`, 0 오차로 세탁 금지 |
| 카메라 추종 | 목표 pan/dolly 방향·시점, 객체 상대 이동, 시작/끝 framing | 카메라 이동 vs 피사체 이동 혼동을 별도 표기 |
| 접촉 정확도 | 접촉 시각/대상/점의 위치 일치, 손·발·소품 변형 | 2초 target event ±시간오차, 접촉 오류 프레임 별도 기록 |
| 동작 자연스러움 | 사람이 1~5 척도, 관절 끊김/경직/비현실적 가속 기록 | 점수 + 이유 및 프레임 인덱스 |
| 프록시 전이 | 영상에 원통·클레이/괴상한 몸통·debug grid가 남는가 | **치명적 아티팩트** 여부 |
| 인물/소품 외형 | 첫 실사 참조와의 일관성(정면·측면·가림), 얼굴 검사 보조 | 얼굴 미검출은 pass 아님 |
| 화질/시간/VRAM | 공간·시간 일관성, flicker, 실제 wall-clock, peak VRAM/OOM | 품질과 속도 다른 지표로 판정 |

**의사결정:** 프리비즈 없는 baseline 대비 주요 동작·공간 지표가 나쁘지 않고 자연스러움·프록시 오염이 수용 가능한 경우에만 해당 `profile + channel`을 기본값 후보로 승격. 정량 임계값은 최소 파일럿 데이터 후 A0/A5가 미리 등록하여 결정; 값 임의 확정 금지.

## 기록 템플릿 (기능 개발 이후 로컬 파일로 생성)

```json
{
  "experiment_id": "p2-previs-e1-001",
  "scenario": "E1", "shot_id": "shot-001",
  "previs_profile": "coarse", "guide_channel": "sparse_rgb_anchors",
  "seed": 123, "frames": 121, "fps": 24,
  "model_id": "<exact-checkpoint>", "model_sha256": "<sha256>",
  "conditioning": {"first_image_sha256": "<sha256>", "guide_frames": [], "strength": null},
  "runtime": {"elapsed_seconds": null, "peak_vram_gb": null, "oom": null},
  "metrics": {"root_error": null, "camera_adherence": null, "contact_error": null, "proxy_leakage": null},
  "human_review": {"verdict": "pending", "notes": "", "reviewer": null}
}
```

위 항목은 실제 run/manifest 계약이 동결될 때 `P2_CONTRACTS.md`와 맞출 것. 예시 `null`은 측정되지 않았다는 의미. 실제 이미지/영상·참조 파일을 Git에 커밋하지 않는다.

## 결과 보고 시 반드시 표시
- `not_run`(실행하지 않음), `blocked`(설치/모델/예산 장애), `done_technical`(영상 생성 성공), `accepted_visual`(품질 육안 합격) 구분.
- 실험이 Seedance 2.5 기반인지, 씨네목화 LTX-2.5 기반인지 명시.
- 학습/생성 모델 호환, 다운로드 및 모델 라이선스 검토 근거 링크를 run과 연결.
