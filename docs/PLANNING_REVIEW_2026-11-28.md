# 씨네목화 전체 Markdown 문서 점검 — 2026-11-28

> 범위: `main@89f46be` 기준 **기존 Markdown 32개 전체를 열람·분류**했고, Blender 정적 레이아웃(`layout3d.py`), LTX 가이드(`animate.py`), 모델 가용성(`config.py`)과 대조했다. 사용자가 제공한 릴스 이미지는 **Seedance 2.5 실험 소개 캡처**로 해석하며 자체 효과 검증 결과로 취급하지 않는다.
> 이번 작업은 **기획/MD 문서 수정**이며, 기존 Python 실행 코드와 GPU 생성 시험은 변경·실행하지 않았다.

## 핵심 진단

1. 기존 P2는 프리비즈 **RGB/depth/pose/tracks 생성 계획**은 있으나, **언제 얼마나 복잡한 geometry를 보여줄지**를 규정하지 않는다.
2. 정교한 proxy 모델링을 영상 모델이 참고하는 방식에 따라 **행동 자유도·정체성·외형 전이**가 상충할 수 있다. 카메라/root 경로의 정밀도는 메시 디테일과 독립적으로 유지해야 한다.
3. '역동적인 액션은 단순 원통'은 **유용한 기본 가설**이지만 손목 잡기·타격·무기 접촉처럼 정확한 신체 접점이 필요한 샷에는 부족할 수 있다.
4. '섬세한 동작=완성형 전신 3D'도 부정확하다. 표정·눈·피부·머리카락은 실사 참조와 영상 생성의 책임이고, 필요한 손목·시선 등만 제어한다.
5. 현재 `engine/animate.py`는 `LTXVAddGuide` **단일 이미지 앵커** 입력을 제공할 뿐, Blender의 전 프레임 애니메이션을 LTX Layout-to-Render/IC-LoRA로 받아 전체 모션을 보존하는 경로는 미구현.
6. `engine/layout3d.py`는 Blender **정지 PNG**. 기존 프리비즈 구현으로 잘못 표기하면 안 된다.
7. P1에서 debug label/grid가 SDXL 결과에 번졌던 이력을 고려해 **최종 guide와 디버그 렌더를 분리**해야 한다.
8. 공식 Seedance 권장과 LTX 전용 어댑터의 기술 가능성은 출처가 분명하지만, 씨네목화 GPU 12GB에서의 실제 결과·시간은 아직 미검증.

## 점검한 32개 원본 MD(모두 역할·적용 여부 정리)

| 구분 | 파일 | 이번 조치 |
|---|---|---|
| 에이전트 입구 | `AGENTS.md` | 적응형 정책 읽기·검증 규칙 추가 |
| 저장소 입구 | `README.md` | 새로운 기획/상태 안내 추가 |
| 호환 문서 | `docs/AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CONTEXT.md` | 호환 링크이므로 **중복 기획 작성 금지**, 정본 인용 구조 유지 |
| 현행 길잡이 | `docs/DOCS_INDEX.md`, `docs/PROJECT_CONTEXT.md` | 이번 연구·실제 구현과 구분·문서 지도 반영 |
| 현행 P2 정본 | `docs/P2_REQUIREMENTS.md`, `docs/P2_ARCHITECTURE.md`, `docs/P2_CONTRACTS.md` | profile/guide channel 분리와 계약 초안 추가 |
| 작업/품질 정본 | `docs/P2_ROADMAP.md`, `docs/P2_TEST_PLAN.md`, `docs/TEAM_PLAYBOOK.md` | A2/A4/A5 역할·H-021/022 실험·단계 게이트 추가 |
| 기존 문서 진단 | `docs/PLANNING_AUDIT_2026-11-26.md` | 당시 점검 이력 보존. 이 문서가 **신규 추가 진단** |
| 과거 제품/기술 요구 | `docs/DESIGN.md`, `docs/PRD.md`, `docs/TASKS.md` | 11/13~21 당시 기획/결정 로그 **원문 보존**, 기존 최신 문서 안내를 우선 적용 |
| 과거/현재 실행 기록 | `docs/ENVIRONMENT.md`, `docs/FINAL_REPORT.md`, `docs/HANDOFF.md`, `docs/HANDOFF_P2.md`, `docs/SESSION_LOG.md`, `docs/WORKLOG.md` | 설치·실측 기록을 재작성하지 않음. 새 기술은 미실측으로만 표시; HANDOFF_P2는 새 방향 링크 보강 |
| 설계 연구 | `docs/design/3D_GUIDED_REALISM.md` | P1 정지 도면 실험 보존·P2와 구분 |
| 설계 연구 | `docs/design/IDENTITY_FIRST_PIPELINE.md` | 2026-11-21 연구 초안 보존, adaptive 정책 정본 링크 추가 |
| UI/디자인 | `docs/design/DESIGN-PLAN.md` | 향후 UI에서 per-shot profile override 필요; H6로 분리, 현재 화면 구현으로 단정 금지 |
| 에이전트 프롬프트 | `docs/prompts/handoff-qone.md` | 과거 고정 상태·브랜치 경로이므로 직접 재사용 금지, AGENTS/DOCS_INDEX 우선 |
| 공용 디자인 스킬/프롬프트 | `docs/prompts/computer-use-figma.md`, `docs/prompts/design-method-skill.md`, `docs/prompts/design-to-figma-playbook.md`, `docs/prompts/figma-uiux.md` | 영상 프리비즈와 직접 관계 없어 수정 불필요. 이들을 프리비즈 지침으로 해석하면 안 됨 |
| P1 엔진 인계 | `engine/README.md` | P1 코드 이력 보존, 현행 P2 프리비즈 설계와 구분 |

## 새롭게 확립할 정본(2026-11-28)

- [ADR-001](adr/ADR-001-adaptive-previs.md): '최저 필요 정밀도' 결정 근거 및 보류 항목.
- [ADAPTIVE_PREVIS](design/ADAPTIVE_PREVIS.md): `none / coarse / joint_lite / geometry_rerender`, 제어 채널·프롬프트·반례 및 실패 규칙.
- [P2_PREVIS_VALIDATION](experiments/P2_PREVIS_VALIDATION.md): Seedance → LTX **외삽 금지**와 동작·접촉·표정·카메라 A/B 실험 설계.
- [A2 Blender 상세](specs/PREVIS_A2.md), [A3 외형 상세](specs/APPEARANCE_A3.md), [A4 LTX 가이드 상세](specs/LTX_GUIDE_A4.md), [A5 평가 상세](specs/QUALITY_A5.md)로 파트별 구현 경계를 정의.
- 현행 요구사항/아키텍처/계약/로드맵/테스트/협업/에이전트 문서를 위 정본에 연결.

## 의도적으로 수정하지 않은 내용

- 2026-11-21 P1에서 실제 생성한 영상 및 `guided-50` 자동 WARN·육안 미승인. 성공으로 바꾸지 않는다.
- 기존 P1 '완전 무료·무제한·음성 우선·M-A/M-B/M-C' 원래 제품 비전과 D1~D72 결정 로그. 신규 실험으로 과거 기록 삭제·덮어쓰기 하지 않는다.
- Figma/디자인용 실행 프롬프트. 프리비즈 기술 지침을 UI 디자인 프롬프트에 복제하지 않는다.
- P2 Layout IC-LoRA의 '승인제·가중치 없음'은 2026-11-21 기록 시점 정보. 현재 접근 가능성을 다시 검증해야 하나 **실제 설치·GPU 시험은 아직 안 함**.

## 검증 상태

**문서 검토는 수행**. 실제 `H-002` 계약 코드 / Blender 풀 3D / LTX 가이드 경로 / A/B 실험·품질·성능은 **이번 작업에서 수행하지 않음**. 따라서 개선된 기획의 기술적 성공 여부는 미확정이다.

소스 참고: [BytePlus Seedance 2.5 공식 가이드](https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide), [LTX Layout to Render](https://docs.ltx.io/open-source-model/vfx-post-production/layout-to-render/), [LTX Motion Control](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control/).
