# 문서 지도 및 우선순위 — 씨네목화

> 2026-11-26. 목적: 다음 세션/에이전트가 오래된 지침을 최신 계획으로 오인하지 않게 한다.

## 어떤 문서를 언제 읽나?

| 상태 | 파일 | 역할 |
|---|---|---|
| **필수: 작업 원칙** | `../AGENTS.md` | 모든 에이전트의 시작점 |
| **현행 요약** | `PROJECT_CONTEXT.md` | 실제 구현·계획 상태, 기술 제약 |
| **검토 결과** | `PLANNING_AUDIT_2026-11-26.md` | 모순/누락/위험과 개선 조치 |
| **P2 요구사항 정본(계획)** | `P2_REQUIREMENTS.md` | 목적·범위·기능·비기능·게이트 |
| **P2 설계 정본(계획)** | `P2_ARCHITECTURE.md` | 단계 연결, 소유 모듈, 오류 처리 |
| **P2 통합 계약(계획)** | `P2_CONTRACTS.md` | 파일 스키마, 식별자, 데이터 산출물 |
| **P2 실행 로드맵(계획)** | `P2_ROADMAP.md` | 단계·티켓·선행조건·DoD |
| **P2 품질 게이트(계획)** | `P2_TEST_PLAN.md` | 자동/육안 검증, 성능 기준 |
| **협업 방식(계획)** | `TEAM_PLAYBOOK.md` | 담당 역할, 작업 병렬화, PR 및 통합 |
| **현재 P2 구현 근거** | `HANDOFF_P2.md`, `../engine/{photo,animate,facegate}.py` | 독립 모듈, 시험 기록 및 미완료 |
| **현재 P1 구현 근거** | `../cli.py`, `../engine/README.md`, `WORKLOG.md` | 실행 중인 Wan 경로 및 실측 |
| **역사적 제품/설계** | `PRD.md`, `DESIGN.md`, `TASKS.md`, `HANDOFF.md` | P1 중심 당시 결정·기능 요구·기록 |
| **연구·아이디어** | `design/IDENTITY_FIRST_PIPELINE.md`, `design/3D_GUIDED_REALISM.md` | 선택 이유, 미검증 기술 가설 |
| **UI 설계 참고** | `design/DESIGN-PLAN.md`, `prompts/` | UI 목표, 이전 에이전트 안내(현행 기준 아님) |

## 2026-11-28 Adaptive Previs 업데이트

| 상태 | 파일 | 역할 |
|---|---|---|
| **현행 P2 프리비즈 상세 설계(계획)** | [`design/ADAPTIVE_PREVIS.md`](design/ADAPTIVE_PREVIS.md) | 샷별 proxy 복잡도, 컨트롤 트랙·실사화 분리, LTX 전달 채널 |
| **근거 결정(검증 전 가설)** | [`adr/ADR-001-adaptive-previs.md`](adr/ADR-001-adaptive-previs.md) | coarse 기본 가설과 경계 조건/되돌림 |
| **P2 기술 실험 설계** | [`experiments/P2_PREVIS_VALIDATION.md`](experiments/P2_PREVIS_VALIDATION.md) | 달리기·접촉·표정·카메라 장면 비교, 모델/시간/사람 게이트 |
| **전 Markdown 32개 검토 기록** | [`PLANNING_REVIEW_2026-11-28.md`](PLANNING_REVIEW_2026-11-28.md) | 기존 문서 분류·오류·보존/변경 근거 |
| **A2 상세 설계** | [`specs/PREVIS_A2.md`](specs/PREVIS_A2.md) | Blender control/render 계층, coarse·joint_lite·clean RGB |
| **A3 상세 설계** | [`specs/APPEARANCE_A3.md`](specs/APPEARANCE_A3.md) | 외형 참조/키프레임/승인 및 프록시 외관 분리 |
| **A4 상세 설계** | [`specs/LTX_GUIDE_A4.md`](specs/LTX_GUIDE_A4.md) | 가이드 채널별 어댑터·메타·GPU 실험 |
| **A5 상세 설계** | [`specs/QUALITY_A5.md`](specs/QUALITY_A5.md) | 동작·접촉·프록시 전이 평가 및 오류 분류 |

**우선순위:** 제품 요구/아키텍처/계약 → Adaptive Previs 상세/ADR → 로드맵/테스트/팀 플레이북. 기존 2026-11-21 P1 기술 문서와 UI 프롬프트는 과거 기록으로 계속 보존한다. 신설 문서가 LTX 구현 완료를 뜻하지 않는다.

## 출처 간 충돌 시 처리
1. 실행 여부는 **현재 코드와 재현 가능한 결과**가 우선한다.
2. 앞으로 만들 기능·범위는 **P2_REQUIREMENTS → P2_ARCHITECTURE → P2_CONTRACTS → P2_ROADMAP** 순서로 결정한다. 계약 변경은 이를 함께 반영.
3. 이전 PRD의 `P2 = 음성·자막`과 새로운 `P2 = 하이브리드 파이프라인`이 충돌한다. 신규 계획의 단계 ID는 `H0~H6`, 티켓은 `H-###`를 사용한다. 기존 P0~P7 ID는 역사 기록으로 보존한다.
4. 장기 제품 비전(음성 우선, 장르/립싱크/UI)과 **현재 검증 목표(텍스트+참조 기반 3~5초 단일 샷)**를 구분한다.
5. 모순 발견 시 무언의 재해석 금지. 근거·영향·선택지를 문서와 PR에서 명시하고 통합 담당이 판정한다.

## 문서 변경 규칙
- 현행 계획 변경: 요구사항 ID/ADR → 계약 → 로드맵 → 테스트 → 컨텍스트 순서로 동기화.
- 구현 변경: 코드/테스트 → WORKLOG → 상태표 순서로 동기화.
- 이 문서 세트는 **승인된 개발 코드가 아니라 계획 기준선**이다. 임계값·속도·라이선스는 미검증이면 미검증으로 표기한다.
