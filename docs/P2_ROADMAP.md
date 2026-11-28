# P2 단계별 구현 로드맵과 실행 티켓 — v0.1

> 2026-11-26. 이 문서는 **구현 작업 설계**이지 착수·완료 보고가 아니다. 과거 `docs/TASKS.md`의 P0~P7(그중 P2=음성·자막)과 구분하기 위해 신규 단계는 **H0~H6**, 티켓은 **H-###**을 사용한다.
> 신규 코드 착수는 프로젝트 오너가 승인한 티켓에 한정(D39); 이번 문서 정비 자체가 전체 코드 구현 승인은 아니다.

## 전체 의존 그래프
```text
H0 [기획·문서 정리] ✅ (이번 문서 기준선)
        ↓
H1 [계약·fixture·검증 뼈대]
        ↓
    ┌───┴─────────────────┐
    ↓                     ↓
H2-A [Blender 시간축]   H2-B [외형/참조 자산]
    │                     │
    └─────────┬───────────┘
              ↓
H3 [LTX 가이드 연결 + 단일 샷 E2E + 육안 게이트]
              ↓
H4 [다객체/프레임 앵커] → H5 [다샷/연결/속도] → H6 [API·UI/음성/복수 화풍]
```
**병렬화의 조건:** H1 스키마/계약 테스트 완료 후 H2-A와 H2-B는 병렬 개발 가능. **GPU 연산은 12GB 단일 장비에서 여전히 직렬 실행**. `cli.py`·공용 스키마 수정은 통합 담당 단독.

## 역할 구분
- **PO/Architect (A0):** 제품 목표·범위·ADR·승인·위험 수용. 중요한 UX/품질과 마일스톤의 최종 결정.
- **Integration/Contracts (A1):** schema, manifest, CLI/오케스트레이션, 단계 통합.
- **Blender/Geometry (A2):** 결정론적 3D 씬·시간축 애니메이션·depth/seg/pose/bbox/camera 출력.
- **Appearance/Identity (A3):** 레퍼런스 권리/등록, 이미지 모델, 얼굴 일관성, 사진 앵커.
- **Video/Inference (A4):** ComfyUI-LTX 워크플로, 프레임 가이드, 메모리/성능, 영상.
- **QA/Evaluation (A5):** 계약/단위/통합/성능/시각 리뷰 규격과 검증 자동화.
- **UI/Experience (A6):** 사용자 플로우, 웹/API, UX. H3 이후부터 본격 작업.
> 이는 **추후 AI 에이전트/개발자에 배정할 논리적 역할**이다. 현재 여러 에이전트가 이미 동시 작업 중이라는 뜻이 아니다.

## 티켓 백로그 (각 티켓 = 한 개 PR, 필요한 경우 더 작은 PR로 분해)

| 티켓 | 단계·주 책임 | 파일 소유권(주요 경로) | 선행 | 완료 정의(DoD) | 상태 |
|---|---|---|---|---|---|
| H-001 | H0 A0 기획 정비 | `docs/P2_*.md`, `AGENTS.md` | 없음 | 문서 상호 링크/구현-계획 구분/기준선 게시 | 문서 작업 |
| H-002 | H1 A1 계약 v1 동결 | `engine/p2_contracts.py`, `tests/test_p2_contracts.py` | H-001 | 4개 주요 JSON 정형/거부 테스트, fake fixture | 미착수 |
| H-003 | H1 A1 오케스트레이션 뼈대 | `engine/p2_pipeline.py`, `tests/test_p2_resume.py` | H-002 | GPU 없이 stage DAG/cache/partial resume 동작 | 미착수 |
| H-004 | H2-A A2 Blender **coarse 프리비즈** | `engine/previs.py`, `tests/test_p2_previs.py` | H-002 + H-021 | 복잡한 rig 없이 root/camera 시간축 3~5초 + clean RGB/tracks, debug 분리, ID·프레임 정합성 | 미착수 |
| H-005 | H2-A A2 geometry 패스 | `engine/previs.py`(동일 영역, H-004 후), `tests/test_p2_previs.py` | H-004 | depth/seg + 2D bbox/카메라 스펙과 프레임 정합성. pose 미지원이면 null 명시 | 미착수 |
| H-006 | H2-B A3 자산 레지스트리 | `engine/asset_bank.py`, `tests/test_p2_assets.py` | H-002 | 외형 참조별 entity_id, 경로·해시·출처/승인, 부족 시 후속 차단 | 미착수 |
| H-007 | H2-B A3 이미지 앵커 어댑터 | `engine/photo.py` 및 별도 P2 어댑터 | H-006 + H-004 fixture | 동일 참조/구도 입력, 후보선택 메타/육안 보류, Krea2 1회 실측 | 미착수 |
| H-008 | H2-B A3 얼굴 게이트 | `engine/facegate.py`, `tests/test_p2_facegate.py` | H-006 | 얼굴 없거나 점수 낮음=needs_review, 역치 초과도 육안 미승인 | 미착수 |
| H-009 | H3 A4 LTX **sparse RGB anchor** A/B | `engine/animate.py`, `tests/test_p2_animate.py` | H-002 + H-004 fixture | 동일 seed/첫 실사 프레임 guide 무/유 비교; source/applied 인덱스·proxy leakage 기록. IC-LoRA는 별도 연구 | 미착수 |
| H-010 | H3 A5 공간·시간·화질 평가 | `engine/p2_verify.py`, `tests/test_p2_verify.py` | H-005 + H-008 | 얼굴·bbox 중심 이동·깜빡임·길이 측정, false PASS 방지 | 미착수 |
| H-011 | H3 A1 실제 CLI 연결 | `cli.py` (단독 소유), `engine/p2_pipeline.py` | H-003,005,007,008,009,010 + **H-022 결과 검토** | 5초 단일 샷, 승인된 profile/channel만 실행, manifest/evaluation 및 실패 처리 | 미착수 |
| H-012 | H3 A0+A5 사람 육안 pilot | `docs/WORKLOG.md`, 평가 결과(로컬) | H-011 | reference/guide/output 대조, PASS/FAIL 근거·영상 프레임/조건 기록 | 미착수 |
| H-013 | H3 A4 성능/VRAM 최적화 | `engine/animate.py`, `docs/WORKLOG.md` | H-012 | 12GB/OOM/5초 성능 실측, Q2·해상도·분할 각각 비교 | 미착수 |
| H-014 | H4 A2+A3 다객체 트랙·참조 | `engine/previs.py`, `asset_bank.py`, 분리 계약 테스트 | H-012 | 2인물 또는 사람+소품 ID 유지, 가림/재등장 검사 | 미착수 |
| H-015 | H4 A4 여러 레퍼런스 조건 비교 | `engine/animate.py` 및 독립 실험 코드 | H-014 | MSR/guide 조건별 회귀·시간·메모리, 설치 전 라이선스 점검 | 미착수 |
| H-016 | H5 A1 다샷/재개/조립 | `engine/p2_pipeline.py`, `assemble.py` 어댑터 | H-012 + H-014 | 2~3샷, 컷/연장/샷 ID 보존, 부분 재생성/타임라인 검증 | 미착수 |
| H-017 | H5 A5 다샷 품질·성능 결정 | `p2_verify.py`, `WORKLOG.md` | H-016 | 기존 P1 기준과 품질/시간 비교, Go/No-Go/방향변경 보고 | 미착수 |
| H-018 | H6 A6 UI/API 계약 | `api/`, `web/` (미존재, 신규 합의 경로) | H-012/017 | 입력·진행·결과·오류 UI와 CLI 동일 계약, 승인된 Mock 기반 | 대기 |
| H-019 | H6 A6+A1 음성/자막 | 신규 `engine/audio.py` 등 | H-017 | 기존 FR-05/06/12와 연결, 시간축 기준 테스트 | 대기 |
| H-020 | H6 A0 화풍/장르 확대 | 이미지·영상 모델 어댑터 | H-017 | 실사 파일럿 통과 후 별도 PRD/라이선스·육안 기준 | 대기 |

## 2026-11-28 Adaptive Previs 추가 티켓 / 핵심 경로 수정

> 과거 H-001~H-020의 원래 범위는 삭제하지 않고 다음 개발 티켓을 더한다. **실제 개발 미착수**.

| 티켓 | 단계·담당 | 목표 | 선행 | DoD | 상태 |
|---|---|---|---|---|---|
| **H-021** | H1 A0+A1+A2 | 샷의 `none/coarse/joint_lite/geometry_rerender` 및 프롬프트/가이드 채널 정책 계약 설계 | H-001 | `previs_policy` fixture 및 dynamic/contact/face 사례의 분기 근거·수동 override 테스트; H-002 스키마와 동기화 | 미착수 |
| **H-022** | H2/H3 A2+A4+A5 | 간단 3D vs 최소 관절 vs 가이드 없는 baseline, **같은 seed/첫 프레임/장면 A/B** | H-002+H-004+H-009 스모크 | 한 샷에서 채널 유효성 확인 후 dynamic/contact/face 실험 기록, 3D 색·캡슐 전이·얼굴/경로/자연스러움/실측 비용 비교; Go/No-Go | 미착수 |
| **H-023** | H4 A2+A5 (조건부) | 접촉 샷에서 효과가 입증된 경우에만 `joint_lite` 실제 경로 및 소품/신체 교차 검증 | H-022 채택 + H-014 | 선별 관절만 표현, contact events·tracks·가림 관계 검증, 단일 샷 회귀 | 보류 |

### 기존 티켓 해석 보완

- **H-002:** `previs_policy`/프로필·가이드 채널/앵커 인덱스·재개 키를 스키마 v1에 포함. 확정 전 테스트 fixture만 사용.
- **H-004:** **coarse 정본부터** root/camera 시간축 3D 애니메이션 구현. full body rig부터 만들지 않는다.
- **H-005:** depth/seg/pose 자체가 필요한지 사용 채널과 실험 필요성으로 결정. 디버그/clean guide 분리.
- **H-007/008:** 얼굴·외형은 3D 디테일이 아니라 승인된 참조 이미지·검증의 책임.
- **H-009:** 단순히 `LTXVAddGuide` 노드 실행 성공이 아니라 가이드 없음 대비 **조건 추종·프록시 전이 평가**. IC-LoRA Layout-to-Render/Motion Control은 현재 자산 설치·호환 미검증으로 **별도 연구 티켓**.
- **H-011/H-012:** H-022의 early Go/No-Go 결과를 검토하고 적용한 프로필/채널만 통합. 실패 시 `prompt_only` 대안으로 돌아가고 범위를 재결정.
- **H6 UI:** 사용자가 샷별 profile을 보고 변경할 수 있도록 하되 실제 검증·승인된 옵션만 노출.

세부 설계 [Adaptive Previs](design/ADAPTIVE_PREVIS.md), 실행 계획 [P2_PREVIS_VALIDATION](experiments/P2_PREVIS_VALIDATION.md).

## 마일스톤별 exit gate

### H0: 기획·준비
현재 상태 검증, 근거 기준 문서, 작업 계약, 책임과 파일 소유권, 라이선스 미확정 표현을 정리. 문서 PR만으로 코드/영상 성공 주장 금지.

### H1: 계약 우선
스키마/파일 fixture/단위테스트를 동결. 불법 경로·중복 entity_id·없는 파일·프레임 간격·버전 오류를 차단. **동결 전 GPU 통합 코딩 금지**.

### H2-A: 시간축 Blender
최소 3~5초/24fps, 단일 인물 proxy와 단순 배경, 고정·이동 카메라 2가지 조건. RGB의 실제 시간 변화, 추출 bbox·camera의 정상 추적, 로컬 단독 실행. Blender 정지 이미지 성공을 시간축 성공으로 보지 않는다.

### H2-B: 외형
참조 이미지 1장 → 선정된 키프레임 1장, 타깃/장면 ID 기록, 얼굴 누락·차이 시 차단. H2-A와 H2-B는 통합 전에 각각 mock/fixture에 대해 테스트.

### H3: 첫 끝까지 연결
첫 프레임 + 정해진 guide 프레임을 LTX에 입력, 3~5초 파일 생성, `evaluation.json`, 육안 verdict. 동일 조건에서 guide 유/무를 비교해 **실제 제어 효과**를 확인해야 Go. 단순 영상 생성만으로 완료 아님.

### H4: 객체/정체성 안정화
소품·인물 2개 이상이 프레임별 ID/위치를 유지하는지 검사. 실측 게이트 미달 시 다샷 확장 중단.

### H5: 다샷/길이
단일 샷 안정화 후 2~3샷으로 확대. 15초 ≤70분은 현재 **목표 미충족 위험**으로 관리; 성능·화질이 트레이드오프라면 기획 결정을 별도로 받는다.

### H6: 경험 확장
API/UI/오디오/화풍은 게이트 통과 후 별도 트랙으로 해제. `docs/PRD.md`의 장기 요구를 순서대로 연결.

## 다음 실행순서 (가장 적은 낭비)
H-021 샷별 정책 설계 → H-002 계약·fixture 확정 → H-003 cache/mock runner; 병렬 H-004(coarse Blender)·H-006(실사 참조); H-009 sparse frame guide의 **짧은 기술 스모크**와 H-005/007/008/010; **H-022 모드별 실험/Go-No-Go** → H-011 통합 → H-012 사용자 육안; H-023 접촉 관절 실제 구현은 H-022에서 효과가 입증된 경우에만 진행.

**지금 바로 할 일:** H-002를 첫 독립 구현 티켓으로 확정하고 스키마/fixture/실패 테스트부터 만든다. 기술의 성공 여부가 불확실한 작업을 UI·멀티샷과 병렬로 진행하지 않는다.
