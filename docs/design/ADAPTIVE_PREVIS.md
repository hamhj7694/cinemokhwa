# Adaptive Previs — 샷별 3D 프리비즈 정밀도·제어 설계

> 2026-11-28 · **P2 현행 설계 보완안 / 구현 전 실험 필요**.
> 사용자가 제공한 릴스 스크린샷의 “과도하게 정교한 프리비즈가 액션을 해칠 수 있다”는 사례에서 출발.
> **해당 영상은 Seedance 2.5 사례이며 씨네목화 LTX-2.5 결과가 아니다.**
> 실험 없이 “동적=단순, 섬세=정교”를 확정 규칙으로 채택하지 않는다.
> 상위 문서: [P2_REQUIREMENTS](../P2_REQUIREMENTS.md), [P2_ARCHITECTURE](../P2_ARCHITECTURE.md), [P2_CONTRACTS](../P2_CONTRACTS.md).
> 실험: [P2_PREVIS_VALIDATION](../experiments/P2_PREVIS_VALIDATION.md). 결정 기록: [ADR-001](../adr/ADR-001-adaptive-previs.md).

## 1. 결론 — 최저 필요 정밀도 / 샷별 분리

**프리비즈는 완성형 애니메이션이 아니라, 생성 모델이 지켜야 할 시공간 제약의 최소 표현.**
기본 프로필은 단순한 3D proxy. 단, 접촉·방향·관절·소품 상호작용이 중요하면 필요한 부위만 추가한다.
복잡한 메시는 예쁜 결과를 보장하지 않고 잘못된 proxy의 색·윤곽·비현실적인 관절 동작이 영상에 전이될 수 있다.

중요한 분리:
1. **애니메이션 정보의 정밀도**: 카메라 경로, 캐릭터 root path, 방향, 사건 발생 시각, 접촉점, 가림 관계.
2. **화면에 보이는 3D 형상의 디테일**: 캡슐/구/상자 vs 간단 관절 몸체 vs 완성형 메시.
3. **가이드를 영상 모델에 주입하는 강도·채널**: 텍스트 / 산발 이미지 앵커 / Layout-to-Render / Motion Control.
4. **실사 외형**: 얼굴·의상·소품·배경은 별도 참조 이미지·실사 키프레임에서 정의.

네 요소를 독립적으로 조절해야 한다. **형상은 단순해도 뿌리 위치/root motion·카메라·접촉 타이밍 데이터는 매우 정밀하게 저장할 수 있다.**

## 2. 프로필 (계획; 현재 코드 구현 아님)

| ID | 화면에 렌더되는 3D | 보존할 정밀 데이터 | 초기 추천 샷 | 주의 |
|---|---|---|---|---|
| `none` | 없음 | 샷 길이/텍스트/참조 이미지 | 프리비즈가 오히려 방해하는지 비교할 기준 | 공간 제어 약할 수 있음 |
| `coarse` **기본 가설** | 인물=캡슐 또는 타원형 몸통+머리(필요할 때만), 소품=박스/구; 팔·다리 생략 가능 | root 궤적·카메라·방향·속도·주요 이벤트 시점·object ID | 이동/달리기/쫓기/넓은 화면/큰 카메라 무빙 | 팔다리·접촉을 명확히 그리지 못함 |
| `joint_lite` **조건부** | 캡슐 몸통+머리, **필요한 관절만** 단순 막대/실린더로 표시. 손·발·접촉 지점은 마커/좌표로 분리 가능 | coarse + 최소 관절 위치·손/발 목표·접촉 이벤트·가림 상태 | 잡기/밀기/타격 접촉/정확한 손짓·발 위치 | 모든 동적 액션에 전신 rig를 붙이는 것이 아님 |
| `geometry_rerender` **연구/후순위** | 충분히 완성된 씬·메시·관절, 디버그 선/축·문자 제거 | geometry/pose/depth/seg full | 원본 CG의 구조 자체를 충실히 다시 렌더링해야 할 때 | 일반적인 표정/잔잔한 동작이란 이유만으로 선택 **금지** |

**`joint_lite`는 섬세한 모든 동작을 뜻하지 않는다.** 얼굴 표정·시선·감정의 섬세함은 3D 팔/다리 디테일이 아니라 실사 얼굴 참조·표정 프롬프트·키프레임/영상 모델 검증에 더 의존할 수 있다.

## 3. 샷별 선택은 '역동성'보다 제약 요구로

| 상황 | 화면 proxy 추천 | 반드시 별도 데이터로 정확하게 | 프롬프트가 담당할 것 |
|---|---|---|---|
| 달리기/추격, 인물 간 접촉 없음 | coarse | root path, 속도 변화, 방향, 카메라 tracking, 거리 | 보폭·팔 흔들림·표정·의상 움직임 |
| 격투/밀치기/물체 잡기 | joint_lite | 누가/언제/어디서 접촉, 손목/발목 목표, 방향 전환, 충돌 회피 | 운동학적 자연스러움·빠른 세부 동작·시각 효과 |
| 섬세한 손동작/제품 조작 | joint_lite(상지 위주) | 손과 대상 객체의 상대 좌표·접촉·조작 타이밍 | 손가락/재질의 외형·미세 흔들림(한계 검증) |
| 감정 대사/얼굴 클로즈업 | coarse 또는 none | 시선 방향·머리 회전·카메라·시선 대상 | 표정·눈꺼풀·미세 표정 (실사 참조 기반) |
| 건물/제품 구조 정확성이 핵심 | joint_lite 또는 geometry_rerender(실험) | 치수/축/배치/가림, 정해진 shape | 재질·라이팅·미세 질감 |
| 가벼운 카메라 패닝 B-roll | coarse 또는 none | 카메라 path/타이밍 | 배경 요소의 외관 |

**선택 우선순위:** (a) 카메라/경로만 필요한가? → coarse. (b) 팔다리/물체의 정확한 접촉이 필수인가? → joint_lite. (c) 실제 메시 형상을 다시 칠하는 게 목표인가? → geometry_rerender 연구. (d) 공간 제약이 거의 없는가? → none. 자동 추천은 설명 가능한 규칙 기반 *제안*만 하고 사람이 override 가능하도록 한다.

## 4. 보이지 않는 제약 데이터와 시각 proxy의 분리

Blender에 두 레이어를 둔다.

- **Control layer (정본):** root 위치/회전, camera intrinsics·extrinsics, 타임라인, 2D projection, ground plane, 객체 바운딩, contact events, 최소 joint target, collision/occlusion, entity_id. **렌더 표시와 무관하게 보존**.
- **Render layer (전달용):** `coarse`, `joint_lite`, `geometry_rerender`에서 설정한 최소형 메시를 RGB/depth/seg/pose 등 **채널별로** 표현. 디버그 label, trajectory line, grid, camera frustum, 색상 구분용 채도 높은 도형은 실제 RGB guide에 기본 삽입 금지.
- **Appearance layer (별도):** 얼굴·옷·공간·소품의 실제 외형은 AI 이미지·참조 자산이 결정. 3D proxy 색과 원기둥 외형을 복제하지 말 것을 프롬프트/렌더 채널에서 정의.

`joint_lite`에서 미구현된 손가락·무릎·얼굴 표정을 임의 정밀 포즈로 **보간해서 확정값처럼 기록하지 않는다**. 모르는 것은 `null` 및 `not_specified`로 남기고 모델에 맡긴다.

## 5. 가이드 전달 채널 — 모델별 구분

| 채널 ID | 전달 형태 | 씨네목화 실제 상태 | 검증 포인트 |
|---|---|---|---|
| `prompt_only` | 참조 키프레임+행동/카메라 텍스트(3D 없이) | 비교 대조군 가능 | 지시만으로 공간/행동 재현되는가 |
| `sparse_rgb_anchors` | `LTXVImgToVideoInplace` 첫 실사 이미지 + `LTXVAddGuide` 지정 시점 이미지 | `engine/animate.py` **노드 생성 가능**, Blender 전구간 연동·품질 검증 아직 없음 | 원통 색/형상 전이·앵커 사이 움직임 이탈 |
| `layout_video_ic_lora` | Blender clay/playblast **전체 영상** + Layout-to-Render 전용 IC-LoRA | **현재 의존 가중치 미설치(기존 2026-11-21 기록: 접근 제한)**, 별도 호환성·VRAM 확인 필요 | 연속 카메라/객체 경로 충실도, CG 외관 전이 |
| `motion_track_ic_lora` | 소수 좌표점/궤적 가이드 + Motion Control IC-LoRA | 공식 워크플로 존재하지만 **씨네목화 구현/설치 확인 없음** | coarse에서 손발이 없어도 root·카메라 제어가 가능한가 |
| `union_structural_ic_lora` | Depth/Pose/Edge 등 구조 신호 | 연구 후보, 설치·품질 검증 전 **기본 경로 아님** | 물체 기하·포즈 조건의 충실도 |

**중요:** Seedance 2.5의 영상 참조 기능과 LTX-2.5의 이미지 앵커 노드는 같은 인터페이스가 아니다. Seedance 테스트 결과를 LTX의 정량적 성능 근거로 전용하지 않는다. LTX 공식 Layout-to-Render와 Motion Control은 **서로 다른 전용 어댑터**이므로 설치·라이선스·12GB 실행 가능성을 별도로 확인.

**기존 구현 주의:** `LTXVAddGuide` 호출은 PNG 이미지를 프레임 위치에 주입하는 방식으로 **풀 프리비즈의 매 프레임 모션 제어와 동등하지 않다**. 현재 `LTXVAddGuide` `strength=1.0`을 임의로 높이거나 반복해서 쓰는 것이 좋은 결과를 보장하지 않는다. 실제 적용 인덱스(노드 버전에 따른 허용값), guide 중복·충돌은 H-002/H-009에서 테스트.

## 6. 프롬프트 계약: 무엇을 따르고 무엇을 새로 만들까?

아래는 **영상 모델별 효과 미검증인 프롬프트 템플릿**, 실행 성공 보장 아님.

```text
SCENE: <shot content / temporal beats>
STRUCTURAL REFERENCES:
- Preserve camera framing, movement direction, key event timing and subject paths
  from the approved motion/3D guide.
- When articulated joints or contact events are specified, honor those relations.
- Do not treat the guide's primitive shapes or clay colors as the final character,
  clothing, materials, or environment.
APPEARANCE REFERENCES:
- Use the approved character/object/location images for identity and look.
MOTION DETAILS:
- Generate natural arm/leg motion, weight shifts and secondary movement
  not explicitly constrained by the structural guide.
CONFIDENCE/PRIORITY:
- High priority: <camera/root/contact by shot>
- Flexible: <gesture/face/secondary details>
```

반례: 원통형 블록아웃만 있는데 “한 손이 다른 사람의 왼쪽 손목을 정확히 잡는다”라고 요구하면 **접촉점 정보가 소실**될 수 있다. 이때는 `joint_lite` 또는 명시적 손목/접촉점 트랙 필요.

## 7. 자동 추천 규칙(우선 사람 검토)

```text
if requires_exact_mesh_rerender:
    profile = geometry_rerender    # 실험/가용 모델 필요
elif requires_contact_or_precise_limb_target:
    profile = joint_lite
elif requires_camera_or_root_motion:
    profile = coarse
else:
    profile = none_or_coarse_by_A_B
```

- '역동적' 여부는 **보조 신호**일 뿐 직접 분기 조건이 아니다.
- `profile`의 자동 선택은 사용자가 수정할 수 있어야 하며, 선택 사유·샷별 품질 측정·최종 수동 승인 기록.
- H2 파일럿에는 **coarse만 구현**하고 contact는 별도 트랙 메타로 표현해 본다. `joint_lite`는 contact 시험에서 실질적인 개선이 있을 때 확장.
- A2는 Blender control/render, A3는 외형/참조, A4는 가이드 채널/시드, A5는 평가, A1은 계약/통합, A0는 프로필 채택 여부를 결정.

## 8. 기존 P1과의 관계

- `engine/layout3d.py`는 **정지 프레임**을 Blender로 렌더한 P1 기준. '프리비즈 시간축 구현'이라고 적지 않는다.
- `engine/previs.py`는 아직 미구현. 이번 문서는 P2의 신규 설계로 **실행 코드 변경 없음**.
- 이전 P1에서 라벨/격자선이 img2img에 번지는 문제를 실제 경험. **디버그 geometry와 모델 전달용 깨끗한 guide를 분리**하는 이유이다.
- P1 SDXL/Wan를 지우지 않고 비교 기준으로 유지한다.

## 9. 검증 실패 시 돌아갈 곳

1. `coarse`에서 동작이 부정확 → root/camera/시간축 데이터가 올바른지 먼저 확인. 문제가 없으면 구조 제어 채널을 변경하거나 `joint_lite`를 시험.
2. `joint_lite`에서 행동이 딱딱하거나 팔다리가 전이됨 → visible proxy를 줄이고 별도 joint tracks/pose 채널을 시험.
3. 특정 RGB guide의 색·캡슐 모양이 영상에 잔존 → 가이드 형상 단순화 **뿐 아니라 전달 채널 변경**; 프롬프트만으로 해결됐다고 단정 금지.
4. 얼굴이 달라짐 → Blender 형상을 키우지 말고 기준 이미지·사진 모델·정체성 게이트를 점검.
5. 모든 가이드 방식이 실패 → 프리비즈 제어는 보류하고 기준 이미지+prompt_only 경로로 회귀, 원인과 비용을 기록.

## 10. 근거/외삽 한계

- BytePlus **Seedance 2.5 공식 가이드**: 단순 기본 도형의 coarse 3D 가이드 권장. 완성형 메시 재렌더링용 fine 3D 모드도 별도 설명. <https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide>
- **LTX 공식 Layout-to-Render**: clay/playblast 영상과 art-directed 첫 이미지로 카메라·배치·동작 조건을 구성. <https://docs.ltx.io/open-source-model/vfx-post-production/layout-to-render/>
- **LTX 공식 Motion Control**: sparse track를 guide video로 변환하는 별도 IC-LoRA 워크플로. <https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control/>
- **LTX Workflow & Asset Compatibility**: 전용 workflow/모델의 버전·호환성 조건을 확인할 것. <https://docs.ltx.io/open-source-model/reference/workflow-asset-compatibility/>
- 위 공식 문서는 **기술 존재·권장 사용법의 근거**이지 3060 12GB에서 성능/품질 PASS라는 증거가 아님.
