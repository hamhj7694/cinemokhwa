# A4 — LTX-2.5 프리비즈 가이드 어댑터 상세 설계 (구현 전)

> 담당 A4 / 선행: H-002, H-004 fixture, H-021 정책 / H-009·H-022 티켓.
> 기준: [Adaptive Previs](../design/ADAPTIVE_PREVIS.md), [계약](../P2_CONTRACTS.md), [A/B](../experiments/P2_PREVIS_VALIDATION.md).
> 현재 `engine/animate.py`는 독립 ComfyUI workflow 생성 및 LTX 25f 텍스트 전용 스모크만 확인됨. **P2 프리비즈와 E2E 결합 미확인.**

## 절대 혼용 금지: 가이드 채널

| 채널 | 실행 형태 | 현재 구체적 상태 |
|---|---|---|
| `prompt_only` | 이미지+텍스트, Blender guide 전달하지 않음 | baseline/실험 대조군 |
| `sparse_rgb_anchors` | `LTXVImgToVideoInplace` 첫 실사 frame + `LTXVAddGuide` 이미지/인덱스 | 노드 배선 코드는 있으나 3D 효과/위치/유효 frame range 검증 필요 |
| `layout_video_ic_lora` | clay/playblast **전체 영상** + 전용 Layout-to-Render IC-LoRA + art-directed first frame | 2026-11-21 모델 파일 접근 실패 기록. 현재 다운로드 가능 여부·GGUF 조합·VRAM 확인 안 됨 |
| `motion_track_ic_lora` | root trajectory/sparse 2D points → 전용 track IC-LoRA | 공식 문서상 기능 존재; 씨네목화 환경 설치/테스트 확인 안 됨 |

`LTXVAddGuide`로 RGB 한두 장을 넣는 것은 매 프레임 움직임 가이드와 동일하지 않다. 형상의 복잡도를 바꾸는 테스트와 LoRA 채널을 바꾸는 테스트를 혼합하지 않는다.

## 입력 객체 / 결과

입력: `scene_spec.shots[].previs_policy`, `tracks.json`, `photo/<shot_id>/keyframe.png`, `guide_channel`, `clean_guide`, allowed anchor frames, `seed`, `model_id`, time/FPS/frames. 객체 ID는 text/reference/track에서 일치해야 한다.
결과: `clips/<shot_id>.mp4`, `guide_application.json`(채널, 모델/LoRA 및 file sha, original/applied frame indices, strengths, first frame digest, 실행 시간, 오류, fallback 원인, image artifact digest).

예시 매핑:
```text
frame_idx 0..N-1 [24fps] -> Blender canonical timeline
  prompt_only: no guide
  sparse_rgb_anchors:
    first photoreal frame = frame 0
    sampled clean guide frames = adapter validated indices only
    record (source_frame_idx, applied_frame_idx) pairs
  layout_video_ic_lora: full clean clay video (only when installed/verified)
  motion_track_ic_lora: sparse root/point tracks with compatible guide node
```

## 구현/실험 단계

1. ComfyUI `object_info`, installed node API, checkpoint/adapter source/license 및 모델별 dtype/GGUF 호환성 재확인.
2. 테스트 케이스 E1 `prompt_only` 기준 25f smoke와 3~5s 실제 장면 준비; 25f 결과는 액션 품질 판단 불가.
3. `sparse_rgb_anchors`는 **동일 첫 프레임/모델/프롬프트/seed**에서 앵커만 추가하고 디코딩 출력 위치/길이·모델 메타·FPS·실측 벽시계 기록. 값/형상/채도가 최종 영상에 전이되면 채널/모드별 원인을 분리.
4. 접촉 E2는 `joint_lite` 시나리오가 준비된 후, 같은 채널/같은 guide strength에서 coarse와 비교.
5. `layout_video_ic_lora`는 **별도 브랜치**에서 공식 가중치 접근 및 12GB 실행 가능성을 확인한 뒤에만 시험. 기존 `sparse_rgb_anchors` 성공으로 이 단계를 완료 처리하지 않는다.
6. `motion_track_ic_lora`는 기능 지원/필요 checkpoint를 공식 문서로 확인하고 Blender root data를 2D point guide로 변환하는 실험을 별도 수행.
7. 실패 시 적법한 `prompt_only` baseline으로 돌아가고 `status=blocked/failed/needs_review`를 구분.

## 안전/검증/캐시
- 더 많은 guide strength=더 높은 품질이라는 단조성 가정 금지. 모델마다 LoRA와 노드가 서로 다른 strength 의미를 가짐.
- 기본 코드의 `strength=1.0`은 **기존 배선 사실**, 최적값이 아님.
- 안 맞는 frame_idx, guide 변환 중 중복/경계 초과, 잘못된 화면 비율, 미설치 LoRA, decoded frame mismatch, OOM → **실패 기록**; 프레임 누락을 보간해 성공 처리하지 않음.
- `profile`, RGB 렌더 스타일, guide channel, first frame, frame_idx map, model/LoRA SHA, prompt, seed, strength 변경은 영상 stage cache 무효화.
- `coarse`가 joint_lite보다 더 좋다는 주장에는 **서로 다른 seed 2회 이상 반복 및 사람의 시각 평가** 필요. 확인하지 못하면 미확정 표기.

공식: <https://docs.ltx.io/open-source-model/vfx-post-production/layout-to-render/> · <https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control/> · <https://docs.ltx.io/open-source-model/reference/workflow-asset-compatibility/>.
