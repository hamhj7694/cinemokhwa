# 씨네목화 다중 에이전트·분업 개발 플레이북

> 2026-11-26. 실제 팀 구성 확정 문서가 아니라 **추천 협업 프로토콜**. 에이전트별로 병렬화해도 통합 제어는 단일 오너가 수행한다.

## 1. 역할/산출물/금지 경계
| 역할 코드 | 담당 | 읽을 문서 | 주 소유 파일 | 건드리지 말 것 |
|---|---|---|---|---|
| A0 Product/Architecture | 요구사항·ADR·범위·게이트 판정 | 전체 기준 문서/결과 | `docs/P2_*.md`의 기준선 관리 | 테스트 없이 성능·품질 승인 |
| A1 Contracts/Integrator | schema/manifest/cache/P2 CLI/PR 병합 | contracts/architecture/roadmap | `engine/p2_contracts.py`, `engine/p2_pipeline.py`, `cli.py` | 기존 P1 경로 무단 변경 |
| A2 Blender/Geometry | 3D 시간축·카메라·pose/seg/depth/tracks | architecture/contracts/test | `engine/previs.py`, `tests/test_p2_previs.py` | `cli.py`·사진·영상 모듈 |
| A3 Appearance/Identity | 기준 사진, asset registry, 사진 모델, 얼굴 게이트 | req/contracts | `engine/asset_bank.py`, `engine/photo.py`, `engine/facegate.py` | 3D 좌표·ComfyUI 전체 자원 총괄 |
| A4 LTX/Inference | 첫 프레임/가이드 연결, 영상 생성, OOM·시간 | architecture/contracts/test | `engine/animate.py`, `tests/test_p2_animate.py` | `cli.py`, asset DB |
| A5 QA/Test | unit/mock/metric/실측·육안 표준 | contracts/test | `tests/test_p2_*.py`, `engine/p2_verify.py` | 오너 대신 육안 승인 |
| A6 UI/API | 이후 UI/API/오디오·진행상태 | roadmap/legacy PRD/UI 가이드 | 새 `api/`, `web/` 경로(승인 후) | H3 gate 이전 완성형 UI 주장 |

- 한 에이전트=한 명의 사람이라는 뜻은 아니다. 같은 사람이 순서대로 역할을 맡을 수 있다.
- 코드 주 소유자가 둘 이상 지정될 경우 **티켓의 순서를 명시**하고 같은 파일에 동시 작업하지 않는다.
- **GPU 한 대에서 각 에이전트별로 동시 렌더 금지**. 모델 설치/업데이트도 통합 담당 배정 시간에 직렬 실행.

### 2026-11-28 Adaptive Previs 분업 규칙

- **A0 제품/연출:** 샷별 '꼭 맞춰야 할 것'(카메라, root, 손·소품 접촉, 얼굴)을 정하고 `previs_policy` 최종 승인. **역동성만으로 coarse/fine 결정 금지**.
- **A1 계약/통합:** `previs_policy`, `source_frame_idx`, `applied_frame_idx`, `guide_channel`, `clean_guide` 및 stage cache digest의 단일 소유자.
- **A2 Blender:** **정밀한 보이지 않는 control tracks**와 **간단한 보이는 proxy**를 분리. 초기 coarse; joint_lite는 필요한 접촉 부위에만. 렌더에는 grid/label/frustum 표시 금지.
- **A3 외형/이미지:** 얼굴·의상·소품·공간 참조의 소유자. Blender 원통 색/shape를 실제 외관 기준으로 오인하지 않도록 키프레임과 asset ID 검증.
- **A4 영상/ComfyUI:** sparse RGB anchors와 추후 IC-LoRA 전체 영상·motion tracks를 **서로 다른 경로**로 구현. 같은 GPU에서 모델 추론 동시 실행 금지. 자산 미설치 채널은 blocked.
- **A5 QA:** dynamic/contact/face/camera A/B 샷, 형태·채도 전이, camera/root/contact 충실도, 일관성/소요 시간, 수치와 사람 육안 판정 구분.
- **A6 UI:** H6에서 **샷별 단순/관절/없음 프로필 수동 변경**과 채널 가용성 표시; 실험 미완료 기능 노출 금지.

상세: [Adaptive Previs](design/ADAPTIVE_PREVIS.md) · [실험 계획](experiments/P2_PREVIS_VALIDATION.md). 신규 H-021/022/023은 [P2_ROADMAP](P2_ROADMAP.md).

## 2. 에이전트 호출용 작업 티켓 템플릿
```text
[Ticket] H-### / 역할 / 상태: ready|blocked
[목표] 사용자에게 보이는 변화 또는 검증하려는 가설 한 가지
[기준 커밋] <sha> / branch <feature/h-###>
[우선 읽기] AGENTS.md, DOCS_INDEX, PROJECT_CONTEXT, P2_CONTRACTS, 대상 소스/테스트
[입력 계약] 파일 경로, schema_version, mock fixture
[출력 계약] 산출물 경로, 메타, 오류 상태
[파일 소유권] 수정 허용 경로만
[선행/차단] H-###, 모델·라이선스·GPU 필요조건
[DoD] 검증 명령(최소 1개), 실패 주입 1개, 산출물 비교
[금지] 이 티켓의 범위 밖 기능, main 직접 수정, 무근거 품질 PASS
[결과 보고] commit, 테스트 결과, 미실행 이유, 로그, 남은 리스크
```

## 3. 병렬 작업을 위한 선행 단계
1. A0+A1+A5: ID·시간축·파일 스키마/버전/fixture를 동결 (H1).
2. A2: `previs` 모듈은 fake `scene_spec`로 개발. A3: 기준 자산/사진 모듈은 fake `previs`로 개발. A4: fake guide PNG로 LTX stage 검증. A5: mock 예제를 독립 제작.
3. A1: 각 프로듀서가 내보내는 **계약 검증**을 먼저 통과한 뒤 실제 통합. 이 전에는 공용 CLI 수정 금지.
4. A0+A5: 실제 GPU 검증을 한 워커에서 직렬 수행하고 기록. 사람 육안 결과 전에는 합격 확정 불가.

## 4. 브랜치/PR/변경 계약
- 브랜치: `feature/h-###-short-name`, 공용 문서: `docs/h-###-...`. 기본 브랜치 직접 개발 대신 PR.
- PR 제목: `H-###: <한 가지 완료 목표>`. 한 PR에 하나의 논리적 계약 변경; 소비자 테스트/fixture 동봉.
- 공용 schema 변경 요청 → A1 단독 PR에서 `P2_CONTRACTS.md` 갱신 및 마이그레이션/호환성 검사. 다른 에이전트는 그 머지를 기다린다.
- 충돌: 오래된 문서의 '완료' 체크를 우선하지 않는다. 변경 실제 diff/테스트/WORKLOG 기반으로 조정.
- 리뷰 순서: API/계약 → 모듈 unit → mock E2E → 로컬 GPU → 사람의 시각 평가 → 상태 문서 업데이트.
- 회귀 실패 시 병합 중지; 사용자가 승인하지 않은 모델 추가/다운로드·외부 전송·유료 API는 금지.

## 5. 1개 단계 작업 후 인수인계
```text
Goal/Scope:
Base SHA / New SHA:
Modified files:
Exact commands + result:
Artifact/run_id/metrics:
Screenshots/contact sheet reviewed? by whom:
Open blockers + next ticket:
Docs updated:
```
인수인계는 새 에이전트가 기억이 없어도 **이 목록과 GitHub만으로** 재현할 수 있어야 한다.

## 6. 개발 과정에서의 결정 관리
- ADR는 `docs/PROJECT_CONTEXT.md`의 결정 요약, 필요 시 `docs/adr/ADR-###.md`로 새로 작성. 최소: 배경/선택지/결정/증거/대안/되돌림 조건/날짜.
- 3D 프레임 가이드가 실패하면 프롬프트만 끝없이 튜닝하지 말고 **입력 앵커 강도·조건 추종·정체성 분리** 중 어느 단계가 실패했는지 먼저 격리한다.
- 신규 도구의 사용권은 모델 버전과 출처를 기록한 뒤 승인. 문서에 적힌 사용 가능 조건이 향후에도 유효하다고 추정하지 않는다.
- PR 리뷰 없이 '전체 파이프라인 완성'이라고 말하거나 README 뱃지를 올리지 않는다.
