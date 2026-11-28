# ADR-001 — 샷별 적응형 프리비즈 및 최소 유효 구속

- **작성:** 2026-11-28
- **상태:** **설계 방향 채택 / 모델별 효과 검증 전 (provisional)**
- **영향:** P2-FR-04/05/08/09/11, H-002, H-004/005, H-009, H-011, H-021/022
- **상세:** [ADAPTIVE_PREVIS.md](../design/ADAPTIVE_PREVIS.md)

## 배경

사용자가 Seedance 2.5 관련 릴스 이미지를 제공하며, 지나치게 정교한 프리비즈가 역동적인 액션을 인위적으로 만들 수 있으니 액션에는 단순 원통·캡슐 proxy를 쓰고 섬세한 동작에만 팔다리 등 정밀 모델을 쓰자는 개선을 제안.

BytePlus 공식 Seedance 2.5 가이드에서도 coarse 3D는 기본 도형을 권장하고, fine 3D는 완성된 3D의 재렌더링용으로 설명한다. 그러나 **현재 프로젝트 모델은 LTX-2.5**이며, 같은 정성적 현상이 일어나는지는 미검증이다.

## 검토한 대안

1. **모든 샷에 정밀한 3D 몸체/전체 리그를 사용:** 구조 정밀도는 높지만 불필요한 제약·비용·비자연스러운 동작 전이 가능.
2. **모든 샷에 몸통 원통만 사용:** 단순하고 빠르나 격투·손목 잡기 같은 접촉 제약 소실 가능.
3. **선택: 최소 화면 geometry + 정확한 제어 정보 + 필요 관절만 추가:** 기본값으로 선택하고 모델별 가이드 강도는 독립 실험.
4. **3D 가이드 없이 텍스트/이미지만:** 품질 비교를 위한 대조군으로 유지.

## 결정(기획)

- **기본 후보=`coarse`**, 접촉·손/발 목표가 필요하면 `joint_lite`, 완성 메시 렌더 충실도가 목표면 `geometry_rerender`(연구), 필요 없으면 `none`.
- **'역동적=coarse/섬세함=full rig' 자동 판정 금지.** 동작의 의미를 정하는 **필수 제어 정보**로 선택.
- Blender 정본의 root/camera/접촉·객체 ID **정밀 데이터**와 AI에 보일 **간소화된 proxy 영상**을 분리.
- 프롬프트와 실사 참조가 외관·비구속 동작을 담당, 영상 모델의 실제 준수 여부는 A/B 실험 후 판단.
- 신규 설계 스키마는 H-002에서 확정하고, 기존 `script.json`, P1 `layout3d.py`는 변경하지 않는다.
- LTX Layout-to-Render/Motion Control은 전용 가중치/워크플로 의존성이 있으므로 **미설치/미검증일 때 기본 경로로 가정하지 않는다**.

## 검증/되돌림 조건

- [P2_PREVIS_VALIDATION](../experiments/P2_PREVIS_VALIDATION.md)에 따라 동일 장면·seed·시작 이미지에서 무가이드/coarse/joint_lite의 궤적·품질·프록시 외형 전이·소요 시간 비교.
- coarse가 일관되게 악화시키면 **가이드 채널을 바꿔 재시험** 후 기본값을 `none` 또는 다른 채널로 수정.
- joint_lite가 접촉 개선 없이 품질·시간을 악화시키면 옵션 보류.
- 실험 결과 없이는 정확도·성능 개선율을 절대 기재하지 않는다.

## 근거

- <https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide> (Seedance에서의 권장; LTX 일반화 금지)
- <https://docs.ltx.io/open-source-model/vfx-post-production/layout-to-render/>
- <https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control/>
- [기존 P1 품질 실패 기록](../WORKLOG.md)
