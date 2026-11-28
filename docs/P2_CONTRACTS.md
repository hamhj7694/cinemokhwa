# P2 인터페이스·파일 계약 — 설계 초안 v0.1

> 2026-11-26. **아직 적용된 코드 스키마가 아니다.** 모든 프로듀서·컨슈머가 이 계약으로 단위 테스트를 통과한 다음 v1로 동결. 코드 변경은 버전/마이그레이션과 함께.

## 식별자·버전
- `run_id`: 한번 생성의 불변 식별자, 파일 경로의 기준.
- `shot_id`: 편집 단위의 안정 ID (`shot`의 표시 문자열과 별개, 장면 1개 이상 포함 가능).
- `scene_id`: 원본 `script.json`의 정수 scene `id`, 보존.
- `entity_id`: 인물/소품/배경 객체의 고유 ID, 전 샷에서 동일 대상에 재사용. Blender `instance_index`와 매핑 필요.
- `frame_idx`: shot 내 0 기반, `fps=24`, 각 모듈에 동일 적용. `time_s=frame_idx/fps`.
- JSON에는 `schema_version` 필수; 경로는 임의 절대 경로가 아닌 **run 폴더 상대 경로**만 기록(외부 참조 원본은 별도 등록).
- 인물/소품 사용 권한·출처·저장 정책, 모델 가중치 해시, 실제 GPU/성능 조건은 출력을 재현할 최소 메타로 기록.

## 2026-11-28 샷별 Adaptive Previs 계약 초안 (H-002에서 확정)

`scene_spec.shots[]`의 optional 정책 블록 `previs_policy` 및 렌더 결과 메타를 다음과 같이 정의 **제안**한다. 이는 **현행 코드 구현 아님**. 기존 필드를 제거하거나 P1 데이터를 깨뜨리지 않는다.

```json
{
  "previs_policy": {
    "profile": "coarse",
    "profile_source": "manual",
    "reason": "camera tracking and root path; no required hand contact",
    "control_priority": {
      "camera": "high",
      "root_path": "high",
      "subject_orientation": "medium",
      "contact": "not_specified",
      "joint_pose": "not_specified"
    },
    "guide_channel": "prompt_only",
    "clean_guide": true,
    "override_reason": null
  }
}
```

- `profile` 허용값: `none | coarse | joint_lite | geometry_rerender` (마지막은 실험/선행조건 필수).
- `guide_channel` 허용값: `prompt_only | sparse_rgb_anchors | layout_video_ic_lora | motion_track_ic_lora`. **설계 후보는 설치/사용 가능 상태가 아님**.
- `control_priority`: `high|medium|low|not_specified`. 필드 없는 신체 부위를 **정밀하게 추정·확정하지 않는다**.
- `profile_source`: `manual|rule_suggested`. 추천 규칙만으로 성공을 주장하지 않으며 사람 override를 허용한다.
- 프리비즈에서 `control_tracks`(정밀 좌표 원본)과 `rendered_proxy`(RGB/depth 등 모델 전달물)를 분리해야 한다. `previs/tracks.json`에 `profile`, `render_version`, `clean_guide`, RGB 생성 설정을 기록한다.
- `frame_idx`는 0기반 24fps 정본. LTX 어댑터에서 앵커 인덱스를 변환하면 `source_frame_idx`, `applied_frame_idx`를 모두 저장하고 **변환 충돌/경계 초과를 실패**로 처리한다. 실제 노드의 유효 인덱스는 H-009 검사 전 확정하지 않는다.
- 가이드 영상/프레임, 프롬프트, source image, guide strength, 모델/LoRA 파일 해시·형상 프로필 변경 시 해당 생성/검증 단계의 캐시를 무효화한다.
- `geometry_rerender`/IC-LoRA는 모델 자산·VRAM·라이선스 점검 통과 후 선택 가능 상태로 전환한다. 불가하면 `blocked` 기록, `sparse_rgb_anchors` 자동 성공 대체로 간주하지 않는다.

상세 [Adaptive Previs](design/ADAPTIVE_PREVIS.md) · [샷별 A/B 실험](experiments/P2_PREVIS_VALIDATION.md).

## 저장 구조 제안
```text
C:/Users/mbc/mokhwa/work/<run_id>/   # run_id must start with p2-
  input/                  # 허용받은 입력 사본/참조 목록(원본을 Git에 커밋 금지)
  script.json             # 기존 Gemma schema:2 원본(읽기 전용)
  scene_spec.json         # P2 정규화 후 장면 정의
  assets/registry.json    # 사람·사물·장소 entity ID → 참조 사진·출처
  previs/<shot_id>/
    rgb/frame_000000.png ...          # 3D 가이드
    depth/frame_000000.exr ...        # 구현 시 optional, depth 단위 명시
    segmentation/frame_000000.png ... # instance_id 컬러맵/매핑 필요
    tracks.json                      # 카메라·bbox/포즈 시간별 메타
  photo/<shot_id>/keyframe.png
  clips/<shot_id>.mp4
  checks/<shot_id>/evaluation.json
  manifest.json
  final.mp4                 # 다샷 단계에서
```
P1 `work/<run_id>` 형식은 계속 보존. P2 `run_id` 자체가 `p2-` 접두어를 가져 경로 중복·P1 충돌을 방지한다.

## 주요 계약(JSON 예시, 실제 값은 단위테스트로 보정)

### `scene_spec.json` — planner → previs / assets / photo
```json
{
  "schema_version": "p2.scene.v1",
  "run_id": "p2-demo-001", "fps": 24, "style": "photoreal",
  "shots": [{
    "shot_id": "shot-001", "source_scene_ids": [1],
    "length_frames": 121,
    "prompt_visual": "man in a grey coat on a rainy street",
    "prompt_motion": "man walks forward, camera tracks slowly",
    "entity_ids": ["char-jun", "place-alley"],
    "camera_intent": "medium tracking shot"
  }]
}
```
기존 `script.json`(`bible`, `scenes[].shot`, `anchors`)을 버리지 않고 변환기로 매핑한다. `scene_spec`의 shot 범위, clip 길이, 단위·타임라인 매핑은 계약 테스트로 보장.

### `assets/registry.json` — identity/appearance
```json
{
  "schema_version": "p2.assets.v1",
  "entities": [{
    "entity_id": "char-jun", "kind": "person",
    "reference_uri": "input/jun_reference.png",
    "reference_sha256": "<sha256>", "license_review": "pending",
    "approved_for_generation": false
  }]
}
```
`approved_for_generation=false`면 후속 단계가 fail-closed. 참조 이미지의 권한 확인과 사람 검토를 기록한 뒤 승인한다. 실제 참조 파일의 출처/동의는 사용자 확인 필요.

### `previs/<shot_id>/tracks.json` — Blender → appearance / animation / verify
```json
{
  "schema_version": "p2.previs.v1",
  "shot_id": "shot-001", "fps": 24, "width": 960, "height": 544,
  "frame_count": 121, "coordinate_system": "blender_world_m",
  "frames": [{
    "frame_idx": 0, "time_s": 0.0,
    "rgb_path": "previs/shot-001/rgb/frame_000000.png",
    "camera": {"position_m": [0,1.6,0], "target_m": [0,1.3,6]},
    "objects": [{
      "entity_id": "char-jun", "instance_id": 1,
      "bbox_xyxy_norm": [0.35,0.2,0.62,0.95],
      "visible": true
    }]
  }]
}
```
`bbox_xyxy_norm`은 0..1 기준 xyxy, 음수/범위 초과 거부. 실제 프레임·객체 가시성·프레임 수 연속 여부 확인. Depth/Segmentation/Pose는 단계별 optional→필수 승격 전 버전 갱신.

### `manifest.json` — orchestrator/캐시
```json
{
  "schema_version": "p2.run.v1", "run_id": "p2-demo-001",
  "pipeline": "hybrid-p2", "status": "partial",
  "stages": {
    "previs": {"status": "done", "input_digest": "<sha256>", "artifacts": ["previs/shot-001/tracks.json"]},
    "photo": {"status": "pending", "input_digest": null, "artifacts": []},
    "animate": {"status": "pending", "input_digest": null, "artifacts": []}
  }
}
```
유효한 `status`: pending/running/done/failed/needs_review. `done`은 파일 존재+해시+검증을 만족할 때만. 각 stage의 elapsed_seconds, 모델/seed/설정/오류 코드를 남김(필수 메타 정의는 H-002 계약 동결).

### `evaluation.json` — verify → 승인자
```json
{
  "schema_version": "p2.eval.v1", "shot_id": "shot-001",
  "metrics": {"face_similarity": null, "track_error_normalized": null, "flicker": null},
  "quality_status": "needs_review",
  "human_review": {"verdict": "pending", "reason": "", "reviewed_at": null}
}
```
숫자 없음(null)은 PASS가 아니다. 다인물·얼굴 없는 샷은 별도 `not_applicable` 상태를 유지해 0으로 강제하지 않는다.

## 모든 단계의 함수 계약(계획)
| Stage | 책임 모듈 | 핵심 입력 | 필수 출력 | 실패/거부 |
|---|---|---|---|---|
| normalize | `engine/p2_contracts.py` 신규 | `script.json`, refs | scene_spec, registry 초기값 | 누락 앵커·중복 ID 거부 |
| assets | `engine/asset_bank.py` 신규 | 원본/승인·출처 | 승인된 registry | 동의/경로 없음 거부 |
| previs | `engine/previs.py` 신규 | scene_spec, registry | RGB 프레임+tracks | 타임축·행렬 오류 거부 |
| photo | `engine/photo.py` 재사용+어댑터 | shot+참조+선정 프레임 | keyframe 및 선택 기록 | 미검증 후보는 needs_review |
| animate | `engine/animate.py` 재사용+어댑터 | keyframe+guide frames+motion | clip+메타 | OOM/노드 오류·범위 이탈 |
| verify | `engine/p2_verify.py` 신규 | previs+photo+clip+refs | evaluation+리뷰 상태 | 수치 미확정은 needs_review |
| assemble | `engine/assemble.py` 재사용 | 승인된 clips | final+timeline | 미승인 샷 거부 |

## 계약 검증 우선 순서
1. `tests/test_p2_contracts.py`: JSON v1 샘플 파싱, 알 수 없는 버전·중복 ID·경로 탈출·프레임 누락 거부.
2. `tests/test_p2_previs.py`: 불변 seed/샷 → 동일 트랙, ID 안정성, 좌표 투영.
3. `tests/test_p2_adapters.py`: ComfyUI 없이 가짜 프레임/메타로 모듈 간 연결 확인.
4. `tests/test_p2_resume.py`: 캐시 재실행과 부분 무효화.
5. 실제 GPU E2E와 육안 판정은 **계약 테스트와 별개**.
