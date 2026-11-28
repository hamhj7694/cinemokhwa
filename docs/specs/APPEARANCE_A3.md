# A3 — 실사 외형·참조 이미지/키프레임 상세 설계 (구현 전)

> 담당 A3 / 선행: H-002, H-006, H-004의 3D fixture / 티켓 H-007·H-008.
> 기준: [Adaptive Previs](../design/ADAPTIVE_PREVIS.md), [공통 계약](../P2_CONTRACTS.md).
> 실제 코드 `engine/photo.py`, `engine/facegate.py`는 개별 생성/점수 기능을 보유하나 Adaptive Previs 통합은 미구현.

## 입력 책임 분리
- `assets/registry.json`: 승인된 원본 참조 사진, `entity_id`, `reference_sha256`, 동의·출처·허용 범위. 미승인 참조는 후속 생성 차단.
- `scene_spec.json`: 누가/무엇을 하는지, 장소/조명/의상/표정, 샷별 `previs_policy`. `none/coarse/joint_lite`는 **외형·실사 수준을 지시하지 않는다**.
- `previs/tracks.json`: camera/root/placement/contact 등, 프리비즈 PNG. 프록시의 회색/원통 형상을 사람의 외형으로 사용하지 않음.
- `photo/reference_look`: 카메라·공간과 양립 가능한 **첫 프레임 또는 키프레임** 생성. 얼굴/의상/소품 소유 ID를 재확인.

## 생성/선별
1. 각 샷의 **첫 프레임과 Blender 첫 프레임의 framing 일치**를 비교. 필요한 경우 ControlNet/구도 조건은 사용 가능한 모델·노드가 확인된 뒤 어댑터별 평가.
2. 기본 후보 Krea2·대안 SDXL·Qwen21(연구용 제약)은 모델별 실제 입력 스키마·라이선스·VRAM 상태를 확인한 뒤 사용. 영상 P2 전체에 배선됐다는 표현 금지.
3. 생성 후보별 seed, 모델 파일 SHA, prompt, 참조 사진 digest, camera target, face detection, 지정된 인물/소품 수, 광원/색을 기록.
4. SFace 얼굴 점수는 **보조 지표**. 얼굴 검출 실패·측면·가림 상태에서 임의 `PASS`를 내지 않는다.
5. 머리·표정·눈·섬세한 피부/의상은 Blender full rig가 아니라 **이미지 참조/프롬프트/영상 모델의 책무**. 첫 프레임에서 3D 원통/그리드 잔존 시 후보 거부.
6. 키프레임 승인 전에는 LTX에 최종 `accepted` 표시 금지. 프로필 변경만으로 얼굴 identity 자산이 새로 생성될 필요는 없음(카메라 구도가 바뀐 경우는 예외).

## 테스트/완료 기준
- 승인되지 않은 참조 → 거부.
- 동일 사람 `entity_id`의 여러 각도 이미지와 첫 프레임 생성에서 인물 수·얼굴·의상 일관성 검사(자동+육안).
- E1 dynamic과 E2 contact에서 실사 첫 프레임을 **고정**해 Blender/LTX 프리비즈 차이 A/B의 교란 요인을 제거.
- `coarse` vs `joint_lite` 이미지 모델 prompt가 동일한 참조 기준을 쓰도록 설정.
- 사람 얼굴이 과도하게 보정되거나 오인된 경우 `needs_review`, provenance 누락·권한 불명은 `blocked`.

본 문서는 가이드 형상의 복잡도에 따른 외형 처리 책임을 규정하며, LoRA 학습을 필수 선행조건으로 만들지 않는다.
