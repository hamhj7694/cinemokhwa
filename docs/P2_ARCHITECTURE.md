# P2 하이브리드 기술 아키텍처 — 계획 정본 v0.1

> 2026-11-26. 대상: **새로운 P2 경로**. P1 Wan 코드 대체/삭제 지시가 아니다. 레퍼런스/3D/영상 경로를 연결하는 **계약 우선 설계**다.

## 핵심 구조와 책임

```text
[TEXT + reference images + optional audio(future)]
              |
[A / Planner] script.json(schema:2) → scene_spec.json
              |
[B / Identity Asset] reference registry / asset bank / face gate
              |                           |
[C / Blender Previs] scene spec + entity registry → animated scene (24fps)
              |  ├─ RGB guide frames / proxy preview
              |  ├─ depth / segmentation / pose / object tracks / camera
              |  └─ object IDs + frame-indexed anchors
              v
[D / Appearance] Krea2 (candidate) | SDXL (fallback) | Qwen21 (research only)
  input: image references + shot prompt + selected previs guide
  output: real-photo keyframe candidates → selection (automated check + human gate)
              |
[E / Motion Render] LTX-2.5 (first frame + indexed guide frames + motion prompt)
  output: sample_video + render metadata; optional layout-to-render/MSR experiments
              |
[F / Validation] identity + geometry/motion + quality + timeline + human review
              |
[G / Assembly] selected shots + FFmpeg → final.mp4 + evaluation + manifest
```

### 기술 경계 — 반드시 지킬 것
- **Blender는 시간축의 공간·카메라·객체 위치에 대한 원천**, 외형·질감·인물 정체성 원본이 아니다.
- **참조 이미지/asset registry가 외형 원천**. 생성형 이미지는 외형을 참조하지만 물리적 좌표/얼굴을 보장하지 않는다.
- **LTX는 프레임 생성기**이고 공간 제어는 조건 입력/강도에 따른다. 객체를 정확히 추적한다고 선전하지 않는다.
- "인물·소품 사진을 3D 물체 표면에 직접 UV 매핑"은 이 아키텍처의 필수 구현 방식이 아니다. 3D 가이드+참조 이미지 기반 생성형 렌더링이 기본이다. 필요하면 별도 렌더러 실험으로 분리.
- `ComfyUI`는 모델 추론 어댑터. `Ollama`는 대본 계획. `FFmpeg`는 인코딩/결합. GPU 소비 단계는 **하나씩** 진행.

## 적응형 프리비즈 정책 (2026-11-28 추가)

- **장면 제작 공통 표현은 샷별** `previs_policy`로 한다. `coarse`(최소 proxy)는 기본 **실험 가설**, `joint_lite`(필수 관절만), `geometry_rerender`(완성 메시 재렌더링 연구), `none`(대조군)을 별개로 기록.
- 동작의 역동성이 아니라 **무엇을 정확히 맞춰야 하는지**로 선택: 추격에는 root/camera, 물체 접촉에는 손목/발목/접점, 얼굴 감정에는 실사 참조·프롬프트. 액션이라고 팔다리가 항상 불필요한 것도, 섬세한 표정이라고 full rig가 필요한 것도 아니다.
- Blender의 정밀한 `camera/root/contact/joint target`과 영상 모델에 전달할 **보이는 RGB proxy 렌더**는 분리. 간단한 캡슐 도형으로 렌더하더라도 root 궤적·접촉 사건·ID·타임코드는 정밀하게 보존.
- `LTXVAddGuide`는 **희소 이미지 앵커**. 이것만으로 영상의 연속 3D 전체 경로를 그대로 따를 수 있다고 가정하지 않는다. Layout-to-Render **전용 IC-LoRA 전체 영상**과 Motion Control **sparse-track IC-LoRA**는 별도 연구·설치·VRAM 검증 대상이다.
- RGB 가이드에는 도형 ID/그리드/카메라 프러스텀/색상 라벨을 입히지 않는다. debug 보기와 AI 입력용 `clean_guide`를 분리하여 과거 P1의 도면 라벨 번짐을 예방한다.
- 가이드 `profile`과 `channel`을 독립 설정하며 미설치 채널을 사용할 수 있는 것처럼 연결하지 않는다. 초기 파일럿은 **coarse로 충분한 단일 이동 장면**부터 검증하고, 접촉 장면에서만 `joint_lite` 후보를 시험.

세부 규격: [ADAPTIVE_PREVIS.md](design/ADAPTIVE_PREVIS.md) · [P2_CONTRACTS](P2_CONTRACTS.md) · [실험 계획](experiments/P2_PREVIS_VALIDATION.md).

## 구현/계획 대조

| 경계 | 기존 코드/근거 | P2 신규 작업 |
|---|---|---|
| A Planner | `engine/script.py`, `schema:2`, `bible`, `shot`, `anchors` | 장면 정규화 어댑터(기존 스키마 비파괴) |
| B Identity | `engine/character.py`, `engine/facegate.py` | entity registry, 참조 소유/출처·다각도 및 승인 플로우 |
| C 3D | `engine/layout3d.py` 정지 PNG만; Blender 4.5.16 백엔드 | `engine/previs.py` **신규**, 키프레임 애니메이션·패스 렌더, 프레임 매핑 |
| D Appearance | `engine/photo.py` 독립 생성 테스트 | 3D 가이드·인물 참조 입력·후처리 기준 검증, 이미지 게이트 |
| E Video | `engine/animate.py` 첫 프레임 + `LTXVAddGuide` 구성 가능 | C/D 결과 전달·frame_idx 정규화·LTX 가이드 A/B, 12GB 스트레스 |
| F Validate | `engine/verify.py` P1 중심, `facegate.py` 별도 | 객체 궤적/시간축/얼굴 유사도 통합 평가·육안 verdict |
| G Assemble | `engine/assemble.py` | P2 결과 적용, 길이/오디오/타임라인 버전 분리 |
| Orchestrate | `cli.py` P1 `mokhwa make` | 별도 `p2 make` 또는 `--pipeline p2` 경로; P1 변경 최소화 |

## stage DAG (완료→무효화 관계)
```text
scene_spec ─┬─> identity_registry ───────────────┐
            └─> animated_previs ─────┐          │
                                     └─> photo_anchor
identity_registry ───────────────────┘     │
                                           └─> LTX_clip ─> verify ─> assemble
animated_previs ───────────────────────────┘
```
- `scene_spec` 변경: 전 단계 무효화. `reference` 변경: 자산/키프레임/클립/평가 무효화.
- Blender의 camera/pose 변화: previs→photo→LTX→평가 무효화.
- 이미지 모델/prompt/seed 변경: photo→LTX→평가 무효화.
- LTX 모델/guide strength/anchor 시점 변경: LTX→평가 무효화.
- 평가 임계값 변경: 영상 재생성 없이 평가만 재실행. FFmpeg fade/CRF 변경: 조립만 재실행.
- 모든 캐시 키는 원본·설정·모델 버전/파일 해시·스키마 버전을 포함한다.

## 시간축과 좌표계
- 파일럿은 **24fps**를 기준으로 `frame_idx = 0..N-1`을 사용. shot의 시작은 0, 전체 편집 타임라인의 절대 시간은 따로 보관.
- Blender 월드 좌표(m)와 이미지 좌표(pixel/normalized)는 다르다. `camera_matrix` 및 렌더 크기로 투영해서 `bbox_xyxy_norm`을 생성.
- 객체는 `entity_id`로 샷 전후 연결. `instance_id`는 패스 렌더의 일시적 번호이므로 유일 ID와 매핑해야 한다.
- 프레임 가이드 샘플링은 LTX 노드 지원 인덱스(예: 8의 배수)로 **어댑터에서 변환**하고 원래 `frame_idx`도 보존한다. 노드 API 제약을 실행 시 재검증한다.
- RGB guide만을 LTX에 넣는 현재 실험 방식이 depth/pose/seg 구조를 완전 보존한다고 가정하지 않는다. 별도 레이아웃 조건(실제 다운로드/라이선스 확인) 도입은 실험적 확장이다.

## 실패 처리와 복구
- fail-closed: 필수 입력·참조 파일·모델·블렌더 패스·노드가 없으면 단계를 실패로 기록; 성공 파일을 위조하거나 빈 이미지를 채우지 않는다.
- 사진 얼굴 미검출/게이트 실패: `needs_review`; 무조건 자동 승인하지 않는다.
- OOM: P2 animate의 Q2 GGUF 폴백은 이미 존재. 실제 결과의 품질/시간/메타를 남기고 별개로 합격 판정한다.
- 일시 오류: stage 상태와 유효한 출력만 재사용. 성공으로 마킹하기 전에 파일 존재·해시·메타 정합성 검증.
- 사용자 판정은 `accepted/rejected/pending`으로 기록. pending은 출시 PASS 아님.
- 모든 출력은 `run_id` 고유 로컬 폴더; 원본 참조 자산 별도 접근/백업 정책.

## 확장 순서
1. 한 사람/한 공간/한 샷 3~5초 → 2. 움직임 궤적·얼굴 정체성 → 3. 다객체/다샷 → 4. 성능/반복 생성 → 5. 오디오·UI·복수 화풍.
단일 이미지/25프레임 스모크 성능을 전체 파이프라인 성능으로 외삽하지 않는다. `P2_ROADMAP.md` 참조.
