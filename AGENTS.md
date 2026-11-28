# AGENTS — 씨네목화 공통 에이전트 지침

> 시행 기준: 2026-11-26 기획 정비. 저장소 루트에서 모든 에이전트가 가장 먼저 읽을 파일.
> 이 문서는 **작업 규칙**이며, 구현 완료를 뜻하지 않는다.

## 먼저 읽기 (순서)
1. `docs/DOCS_INDEX.md` — 정본/과거 문서 구분
2. `docs/PROJECT_CONTEXT.md` — 제품 목표, 사실로 확인된 상태, 주요 제약
3. `docs/P2_REQUIREMENTS.md` — 신규 하이브리드의 제품 범위/수용 기준
4. `docs/P2_ARCHITECTURE.md` — L0~L4, 모듈 분리, 통합 경계
5. `docs/P2_CONTRACTS.md` — 데이터 및 모듈 입력/출력 계약
6. `docs/P2_ROADMAP.md` — 단계/티켓/의존성/완료 조건
7. `docs/P2_TEST_PLAN.md`, `docs/TEAM_PLAYBOOK.md` — 검증 및 팀 협업
8. 작업 대상의 **실제 코드와 테스트**, `docs/HANDOFF_P2.md`, `docs/WORKLOG.md` — 구현 및 실측 근거

## 권위 및 상태 구분
- **현재 구현 사실:** 코드 + 재현 가능한 테스트 + `WORKLOG`/산출물. 문서만 있다고 구현된 것이 아니다.
- **P2 목표 설계:** 본 문서 묶음의 요구사항·아키텍처·계약·로드맵. 목표는 완료 사실이 아니다.
- **기존 P1 설계·실험:** `docs/DESIGN.md`, `docs/PRD.md`, `docs/TASKS.md`, `docs/HANDOFF.md`; 삭제·덮어쓰기 금지, 역사적 근거로만 참조.
- `docs/design/IDENTITY_FIRST_PIPELINE.md`는 P2 기술 연구·아이디어 기록, 위 목표 문서와 충돌하면 별도 이슈로 제기.
- 코드/문서 불일치를 발견하면 자동으로 한쪽이 옳다고 가정하지 말고 `docs/PLANNING_AUDIT_2026-11-26.md`에 준하는 근거와 수정 제안을 남긴다.

## 2026-11-28 P2 프리비즈 정책 (필수)

- P2의 샷별 프리비즈 정밀도는 [ADAPTIVE_PREVIS](docs/design/ADAPTIVE_PREVIS.md)를 먼저 읽는다. **`coarse` 기본은 검증 전 가설**이며, 얼굴·손동작·접촉·카메라 제어가 필요한지에 따라 선택/override.
- **보이는 proxy 메시 정밀도 ≠ 제어 트랙 정밀도**. Blender root/camera/contact 데이터를 보존하되 RGB 전달용 도형은 최소화.
- LTX `LTXVAddGuide`(이미지 앵커)와 Layout-to-Render/Motion Control IC-LoRA(전용 모델)는 **다른 채널**; 사용 가능한 코드·모델·GPU 실측이 없으면 동일하다고 취급하거나 `PASS`로 보고하지 않는다.
- 샷별 `previs_policy`, `guide_channel`, 수동 선택 이유 및 clean/debug 가이드 분리는 [P2_CONTRACTS](docs/P2_CONTRACTS.md)와 [P2_PREVIS_VALIDATION](docs/experiments/P2_PREVIS_VALIDATION.md)을 따른다.
- A2/A3/A4/A5 코딩 착수 시 [파트별 기술 명세](docs/specs/PREVIS_A2.md) / [이미지](docs/specs/APPEARANCE_A3.md) / [영상](docs/specs/LTX_GUIDE_A4.md) / [검증](docs/specs/QUALITY_A5.md) 중 **자기 담당 문서**를 읽는다. H-021 정책·H-002 계약을 먼저 확인하고, H-022 실험은 H-011 통합 게이트에서 확인한다. 기획 승인으로 실험 성공을 주장하지 않는다.

## 작업 시작 규칙
- 하나의 티켓만 수행한다. 티켓 ID, 담당 모듈, 선행조건, 읽을 파일, 산출물, 검증 명령, 금지 범위를 먼저 선언한다.
- 신규 구현은 사용자/프로젝트 오너의 승인된 티켓 범위만 진행한다(D39). **문서 정비 승인은 코드 구현 승인과 다르다.**
- 다수 에이전트는 `docs/TEAM_PLAYBOOK.md`의 역할 및 파일 소유권 계약을 따른다.
- 동시에 `cli.py`, `engine/config.py`, 공용 스키마, `docs/PROJECT_CONTEXT.md`를 수정하지 않는다. 통합 담당자만 병합한다.
- 모든 새 데이터 구조는 `docs/P2_CONTRACTS.md`와 버전을 맞추고 소비자 테스트를 포함한다.
- Windows 10 · RTX 3060 12GB · 32GB RAM, 로컬 우선, GPU 무거운 작업 직렬화.
- 민감한 참조 이미지·원본 음성·생성물·모델 가중치·비밀키를 git에 넣지 않는다. 외부 API 업로드 금지.
- 모델 라이선스는 **배포·상업 사용 전 원문을 재검증**한다. 구 문서의 라이선스 표를 현재 법적 승인으로 취급하지 않는다.
- **숫자 PASS ≠ 시각적 품질 PASS.** 실제 영상 수동 리뷰가 완료되기 전 성공 선언 금지.

## 완료 보고 규격
`티켓 / 기준 커밋 / 변경 파일 / 실행한 테스트(명령, 결과) / 실행하지 못한 테스트 / 산출물 경로 / 남은 리스크 / 다음 의존 티켓`을 적는다.
실측이 있으면 `docs/WORKLOG.md`에 run ID·조건·소요·결과를 갱신한다. 결과 없는 성능 주장은 금지한다.
