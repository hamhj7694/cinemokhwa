# A2 — Blender Adaptive Previs 모듈 상세 설계 (구현 전)

> 담당 A2 / 선행: H-002 + H-021 / 대상 H-004·H-005·H-023(조건부).
> 기준: [Adaptive Previs](../design/ADAPTIVE_PREVIS.md), [계약](../P2_CONTRACTS.md), [실험](../experiments/P2_PREVIS_VALIDATION.md).
> 이 파일은 명세이며 `engine/previs.py`는 현재 **없다**.

## 1. 목표/비목표

**목표:** 24fps 프레임 시퀀스에 대해 camera/root/heading/contact의 정확한 타임라인을 **정본 tracks**로 저장하고, `coarse` 또는 `joint_lite` 같은 필요한 최소 geometry로 clean RGB/depth/seg/pose 가이드를 **선택적으로 렌더**.
**비목표:** photoreal 3D 캐릭터 자동 생성, 완성형 리깅, 원본 표정·손가락 애니메이션 자동 생성, Blender 메시를 실사 완성본으로 직접 변환.

## 2. 구현 대상 아키텍처 (권장 모듈 경계)

```text
engine/previs.py            # public entry: generate_previs(scene_spec, policy, registry, output_root)
engine/previs_control.py    # planned: frame-indexed camera/root/contact/occlusion tracks
engine/previs_geometry.py   # planned: none/coarse/joint_lite proxy geometry builder
engine/previs_render.py     # planned: Blender subprocess + clean/debug RGB/depth/seg export
tests/test_p2_previs.py     # existing plan: contract, frame count, track correctness
tests/fixtures/previs/     # synthetic no-personal-data deterministic examples
```
**이 경로는 제안**이다. 실제 파일 분리는 A1 승인 및 단위 테스트 단순성을 고려해 결정한다. 기존 `engine/layout3d.py`를 P2 코드로 무단 덮어쓰지 않는다.

## 3. 입력/출력

입력: `scene_spec.json`의 `shot_id`, `length_frames`, `fps=24`, `entity_ids`, `previs_policy`(profile 및 priority), `asset registry`의 안정한 entity_id. 카메라/동작 키프레임·접촉 이벤트는 정확한 숫자 또는 구조화된 정의로 확보. 텍스트 프롬프트만으로 정확한 3D 연출을 완성했다고 가정하지 않는다.

필수 출력:
- `previs/<shot_id>/tracks.json`: 모든 frame_idx, camera, entity root pose, bbox_xyxy_norm, visibility; `profile`, `render_version`, `track_source`, 이벤트 시각.
- `previs/<shot_id>/rgb/frame_NNNNNN.png`: **debug 텍스트/축/보색 도형 없이** 렌더한 clean 가이드. `profile=none`에서 RGB 비생성은 정상(명시적 status).
- A1 contract에 의해 해시/경로로 추적 가능한 manifest stage 결과.

선택 출력 (필수처럼 꾸미지 않음):
- depth, instance segmentation + ID mapping, joint targets, occlusion map, 3D/2D bbox, camera matrix, `debug/` 영상.
- 손/발이 존재하지 않는 coarse에서는 `joint` 필드를 생성하거나 가짜 값을 넣지 말고 `not_specified`.
- `joint_lite`에서 접촉 부위 최소 관절 위치만 추가. 관절 변형이 물리적으로 자연스러운지 별도 검사.

## 4. 세부 처리 규칙

1. **Control layer** 생성: 카메라 transform(투영행렬·fov), floor, root path, heading, contact targets/events, entity_id를 독립 저장.
2. 샷의 `previs_policy.profile`로 visible geometry 결정: `coarse` = 캡슐/박스/구/필요 머리만; `joint_lite` = 최소 상지·하지, 직접 의미 있는 관절/접점만.
3. 프레임마다 일관된 단위·좌표(Blender 세계 좌표 m; 2D는 `bbox_xyxy_norm` xyxy 0~1). 카메라 기준 후면·가림 및 뷰포트 밖 bbox는 **명시 상태**를 갖게 한다.
4. Blender headless 렌더는 프로젝트 root 외부 실행 폴더에 저장. 결과물이 24fps, length_frames와 1:1, 연속적인 frame_idx인지 확인. 장면 및 카메라 작업은 **결정론적**. 사용자 파일·원본사진·모델 가중치 Git 저장 금지.
5. Geometry가 없는 곳에 정밀 손가락 위치를 가짜로 보간하지 않는다. Camera/root path가 단순 proxy와 상충하지 않도록 검증.
6. render clean 영상에 debug 요소(글자, 색상 ID, 카메라 프러스텀, path gizmo)는 기본 절대 포함하지 않는다. mask/seg는 **별도 파일**에서만 표현한다.
7. `frames=25` 스모크로 전체 움직임을 검증했다고 하지 않는다. 3~5초짜리 카메라/접촉 시간축 시퀀스 확인이 필요.

## 5. 오류·캐시·DoD

- 입력 불량: unknown entity, 중복 ID, 누락된 frame_idx, FPS 불일치, 접촉 이벤트 범위 초과, invalid camera matrix, path traversal → fail closed.
- `profile`만 바뀌면 **control_tracks가 불변**인지 확인; `rendered_proxy`와 downstream guide/cache만 무효화. `root/camera/contact` 변경 시 control+render+downstream 무효화.
- H-004 DoD: E1 카메라 tracking 3s/5s `coarse` clean RGB + 모든 frame tracks + CPU/Blender 계약 검증.
- H-005 DoD: root/camera/bbox·depth/seg(선택 시)의 프레임 정합성; unknown 관절 false data 없음.
- H-023 DoD(조건부): E2 접촉 geometry·관절 최소 표현, `joint_lite`가 `coarse`보다 실제로 나은지 별도 결과 확인.

## 6. 개발 전 보류·확인

Blender 버전은 과거 4.5.16 LTS 기록. 실행PC 설치 재확인 필요. Python/Blender 접근 경로, CPU/VRAM, 렌더 패스별 포맷, 모델에 전달할 RGB 처리 방식은 H-002/H-004 구현자가 fixture로 확정한다.
