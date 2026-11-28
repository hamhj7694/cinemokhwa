# A5 — Adaptive Previs 품질·원인 분석 명세 (구현 전)

> 담당 A5 / H-010·H-022, 선행 H-002 계약. 프로젝트 오너(A0) 육안 승인 필수.
> 참조: [P2_PREVIS_VALIDATION](../experiments/P2_PREVIS_VALIDATION.md), [P2_TEST_PLAN](../P2_TEST_PLAN.md).

## 검증의 세 가지 분리

1. **프리비즈 자체 품질:** Blender control layer의 frame_idx/camera/root/ID/event timing/visible proxy 대응이 정확한가? ⇒ CPU/3D 통합 테스트.
2. **가이드 제어 충실도:** AI 영상에서 root/camera/접촉/방향/구도가 목표에 맞는가? 가이드 없음보다 유의미하게 개선되었는가? ⇒ GPU A/B.
3. **최종 영상의 표현 품질:** 팔다리·손·표정·소품이 자연스럽고 실사적이며 원통/격자·정체성 오류가 없는가? ⇒ 자동 통계+육안.

한 층의 PASS가 나머지 두 층의 성공을 뜻하지 않는다.

## 평가 매트릭스

| 케이스 | 필수 수치/관찰 | 성공 주장에 필요한 증거 |
|---|---|---|
| E1 달리기/추격 | 프리비즈 vs 생성 영상 bbox 궤적, camera target, 사람의 자연스러움 | frame range 예시 및 무가이드와 같은 시드 비교 |
| E2 손목/소품 접촉 | 정확한 상대 객체 ID와 contact time, 손목 방향, 물체 사라짐/변형 | 접촉 전·중·후 프레임 3곳+원인 기록 |
| E3 표정 | 기준 얼굴의 동일성, 얼굴 찌그러짐·표정·시선·중간 프레임 | 이미지 참조+육안, 미검출은 pass 아님 |
| E4 카메라 | camera pan/dolly vs subject motion | 좌표계/상대 이동 검증, 화면 프레임 비교 |
| 모든 실험 | 시간, 해상도, 모델 가중치, seed, guide profile/channel/strength, peak VRAM, 품질/드리프트 | 동일 조건 비교 + 재현 스크립트/계약 |

## 실패 원인 분류 taxonomy

- `E_CTRL`: Blender control layer/경로/카메라 값 오류.
- `E_RENDER`: RGB guide에 label/색상/그리드·proxy 외형 전이 위험.
- `E_GUIDE`: LTX 앵커 인덱스/신호/LoRA 미적용·왜곡.
- `E_CONTACT`: 손/발·소품 접촉점과 사건 순서 오류.
- `E_IDENTITY`: 얼굴/의상/배경 정체성 변경.
- `E_TEMPORAL`: 움직임 끊김·카메라 경로·플리커·길이 불일치.
- `E_INFRA`: OOM·누락 모델·시간 초과·노드 API 변경.

## 상태·보고 정책
- `not_run` / `blocked` / `failed` / `done_technical` / `needs_review` / `accepted_visual`. 자동 WARN(FAIL 없음)과 사용자 육안 PASS를 혼동하지 않는다.
- `not_measurable`/face missing은 지표 `null`로 표현. 평균 오차를 계산할 때 누락 검출 비율을 별도 보고하고 임의로 0을 넣지 않는다.
- A5는 수치와 contact sheet를 제공하지만 **A0의 사람 육안 승인권을 대체하지 않는다**.
- H-022의 결과가 약하면 무작정 fine 3D를 추가하지 말고 `E_CTRL` vs `E_GUIDE` vs `E_RENDER` 원인을 분리해 다음 변경 티켓을 요청한다.

이번 명세 역시 실제 평가 실행/결과가 아닌 개발 계획이다.
