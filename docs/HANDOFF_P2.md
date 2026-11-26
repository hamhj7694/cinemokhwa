# P2 하이브리드 파이프라인 — 작업 인계서 (다른 PC 이어받기용)

> **역할 구분 (2026-11-26):** 이 파일은 2026-11-21 P2 **설치·독립 시험·실측 기록**이다. 현재 P2 전체 기획/통합 기준은 [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)·[P2_REQUIREMENTS.md](P2_REQUIREMENTS.md)·[P2_CONTRACTS.md](P2_CONTRACTS.md)·[P2_ROADMAP.md](P2_ROADMAP.md)이다. 아직 `p2 make` 및 Blender 시간축 프리비즈 통합이 완료된 것은 아니다.

> 작성 시점: 2026-11-21 / 마지막 커밋: `302f7f1` + 이번 커밋(미생성)
> 이 문서만 읽으면 지금까지의 결정·설치·측정·남은 일을 이어받을 수 있습니다.

---

## 1. 사용자 원문 (절대 훼손하지 말 것)

| 구분 | 원문 |
|---|---|
| 기존 파이프라인 보류 | `지금도 다른 인물 같아. 지금 방식 그대로 하면 완성도 높은 영상 만들기는 어려울 거 같아. 일단 보류하고 다른 신규 파이프라인을 연구해보자!` |
| 신규 방향 | `여러 객체나 인물이나 배경 요소를 핀 처럼 앵커하거나 고정하거나, ltx-2.5 사용하거나, 스테이블 디퓨전쓰거나, 블렌더로 풀 영상 구도 3d 모델링 먼저하고 그 위에 실사를 입히는 방식이나, 혹은 이러한 방식들을 혼합하는 방식으로 진행하자!!!!!!!!` |
| 역할 분리 보완 | `3d로 영상의 틀만 잡고, 그 위에 인물이나 물품, 사물, 배경은 실사 혹은 아주 실사적이고 ai티 안나는 ai 생성이미지사진을 모티브로 해야하는 거 아니야? 내가 잘 못 이해했나?` |
| 이미지 모델 | `krea 2와 큐원-이미지 2.1 써보자! (모델을 토글이나 드롭다운으로 변경할 수 있게하자)` |
| 업무 방식 | 설명은 표 중심, 사용자 확인 요청 금지(명시적 중단 전까지 진행), 설치 필요 시 묻지 말고 바로 설치, 커밋·푸시 메시지에 비전가용 쉬운 설명 포함, 숫자 PASS만으로 통과 불가(육안 우선) |

---

## 2. 결정 사항 (D63~D72 확정)

| ID | 결정 |
|---|---|
| D63~D72 | guided 파이프라인 **보류**, `guided-50` 보존, 재개 지시 전까지 수정 금지. 신규 run은 `p2-*` |
| 정체성 | tuning 문제가 아니라 **구조 문제**. 씬마다 얼굴 생성 금지, 단일 정체성 원본 사용 |
| 3차 개정 | 3D = 카메라·위치·깊이·포즈 **틀만**. 인물·소품·배경의 외형·질감·정체성 = 실사 AI 이미지. 3D 렌더를 LoRA 학습에 쓰지 않음 |
| L0 흐름 | 실사 기준 사진 1장 + 3D 포즈 가이드 24~32개 → Krea2/Qwen21로 같은 사람 사진 생성 → 얼굴 게이트 통과분으로 LoRA 학습 |
| 이미지 모델 | `krea2`(기본) / `qwen21` / `sdxl`(레거시). CLI `p2 make --image-model`, `Config.image_model`, `IMAGE_MODELS` |
| LTX 경로 | GGUF + ComfyUI. DiT `UD-Q3_K_XL`, OOM 시 `UD-Q2_K_XL`. TE는 `gemma4-12b-ltx25-comfy-w4a8.safetensors` (GGUF TE 없음, `CLIPLoader(type=ltxv)`) |
| Krea2 노드 | 기본 ComfyUI-GGUF가 `krea2`를 몰라 `RealRebelAI/ComfyUI-GGUF_KREA-2` **포크** 사용 (city96 노드는 `tools\backup\ComfyUI-GGUF-city96`로 이동 보존) |
| Layout IC-LoRA | HF 승인 필요(`Error: Access denied`) → **필수에서 제외**, 3D 구도는 `LTXVAddGuide` 프레임 앵커로 주입하는 fallback 확정 |

---

## 3. 환경 (다른 PC에서 그대로 재현할 것)

| 항목 | 값 |
|---|---|
| GPU | NVIDIA RTX 3060 12GB, driver 581.15 |
| ComfyUI | `C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI`, v0.45.0, port **8188** |
| Python | `C:\Users\mbc\mokhwa\ComfyUI_windows_portable\python_embeded\python.exe` |
| ComfyUI 실행 | `& "<위 python>" -s "...\ComfyUI\main.py" --windows-standalone-build --disable-auto-launch --port 8188` |
| hf CLI | `C:\Users\mbc\AppData\Local\Python\pythoncore-3.12-64\Scripts\hf.exe` (다운로드 스크립트는 `HF_HUB_DISABLE_XET=1`) |
| 데이터 루트 | `C:\Users\mbc\mokhwa\` (git 레포 밖, D55) |
| Git 레포 | `C:\Users\mbc\Documents\git\cinemokhwa` |

### 설치 스크립트 (순서대로, 묻지 말고 실행)

| 순서 | 스크립트 | 역할 |
|---|---|---|
| 1 | `tools/install_p2_nodes.ps1` | ComfyUI 커스텀 노드 + Krea2 GGUF 포크 (已完成) |
| 2 | `tools/download_p2_models.ps1` | LTX DiT Q3/Q2, gemma4 TE, video/audio VAE, spatial upscaler, MSR V2. Layout LoRA는 `-Optional`로 건너뜀 |
| 3 | `tools/download_image_models.ps1` | Krea2 GGUF+TE+VAE, Qwen21 int8+TE+VAE+Turbo LoRA (已完成) |

---

## 4. 설치된 모델 파일 (models\ 기준, 정확한 이름)

| 경로 | 용도 |
|---|---|
| `unet\distilled\ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf` | LTX DiT 기본 (11.18GB). ComfyUI 로더 이름은 **`distilled\...` 접두어 필수** → `Config.ltx_dit_loader` 사용 |
| `unet\distilled\ltx-2.5-22b-distilled-UD-Q2_K_XL.gguf` | OOM fallback (8.85GB) → `Config.ltx_dit_small_loader` |
| `text_encoders\gemma4-12b-ltx25-comfy-w4a8.safetensors` | LTX 텍스트 인코더 (9.88GB) |
| `vae\ltx-2.5-video-vae-conv-bf16.safetensors` / `vae\ltx-2.5-audio-vae-bf16.safetensors` | LTX VAE |
| `latent_upscale_models\ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` | 2스테이지 업스케일 |
| `loras\LTX-2.5-Licon-MSR-V2.safetensors` | 다중 인물 고정 (LiconStudio/LTX-2.5-Multiple-Subject-Reference) |
| `unet\Krea-2-Turbo-Q5_K_S.gguf` | Krea2 DiT (8.21GB, RealRebelAI 포크) |
| `text_encoders\qwen3vl_4b_fp8_scaled.safetensors` / `vae\qwen_image_vae.safetensors` | Krea2 TE/VAE |
| `diffusion_models\qwen_image_2.1_int8_convrot.safetensors` | Qwen21 DiT (7.26GB) |
| `text_encoders\qwen3vl_8b_w4a8.safetensors` / `vae\qwen_image_2.1_vae_bf16.safetensors` / `loras\qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors` | Qwen21 나머지 |
| `loras\ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors` | **없음** (승인제). 없어도 동작 |

`object_info` 재확인 완료: `UnetLoaderGGUF`, `CLIPLoader(type=krea2/qwen_image/ltxv)`, `TextEncodeQwenImage21`, `ManualSigmas`, `LTXVImgToVideoInplace`, `LTXVAddGuide`, `LTXVAddLatentGuide`, `VAEDecodeTiled`, `ComfyUILTX25MSRICLoRALoader`, `ComfyUILTX25MSRMultiReferenceGuide` 모두 존재.

---

## 5. 실측 결과 (2026-11-21, 12GB 3060)

| 테스트 | 설정 | 결과 | 판정 |
|---|---|---|---|
| Krea2 이미지 | 768×432, 8스텝 cfg1, Q5_K_S | **65.1초** / 1장 | 정상 |
| Qwen21 이미지 | 768×432, 8스텝 turbo LoRA | **230.2초** / 1장 | 정상 (research license) |
| LTX 영상 | Q3 GGUF, 960×544, 25프레임, 8스텝 sigmas, tiled VAE | **530.5초** / 25f, OOM 없음 | 정상이나 **속도 미달** |

| 목표 대비 | 계산 |
|---|---|
| 121프레임 환산 | 42.8분 |
| 15초(≈3클립) | **128분** → 목표 ≤70분 **미달** |
| 대안 (문서 §7 반영) | 스테이지 768×432로 축소(0.64배→82분), Q2 전환, 또는 25프레임 세그먼트 5~6개 + multishot. 최종 1280×704는 업스케일 스테이지에서 처리 |

> 공식 LTX 설정: fps 24, 121 frames, stage1 960×544, `euler_ancestral`, CFG 1,
> sigmas `1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0`,
> tiled VAE `512/64/128/32`. 1280×704는 32·64 배수라 그대로 사용 가능.

---

## 6. 현재 코드 상태 (이번 커밋에 포함되는 파일)

| 파일 | 상태 | 내용 |
|---|---|---|
| `engine/photo.py` | 신규 | 모델별 워크플로 빌더, 4시드 생성, 얼굴 게이트 보조 선택, `visual_review: "REQUIRED"` |
| `engine/facegate.py` | 신규 | `tools/face_identity.py`(YuNet+SFace) importlib 재사용, `similarity()`/`passes()` |
| `engine/animate.py` | 신규 | LTX-2.5 GGUF + 프레임 앵커(`LTXVImgToVideoInplace`+`LTXVAddGuide`) + tiled VAE + Q2 fallback |
| `engine/config.py` | 수정 | `IMAGE_MODELS`, `image_model`, P2 모델 경로, `ltx_dit_loader` 프로퍼티, `face_gate_pass=0.60`, 포토리얼 프롬프트 |
| `engine/comfy.py` | 수정 | `outputs()`가 `gifs`/`videos`도 처리 (SaveVideo 대응) |
| `tools/download_*.ps1`, `install_p2_nodes.ps1` | 수정/신규 | 위 §3 설치 |
| `tools/smoke_photo.py`, `smoke_animate.py` | 신규 | 스모크 테스트 재현용 |
| `docs/design/IDENTITY_FIRST_PIPELINE.md` | 수정 | 3차 개정 + 실측 표 |
| `docs/HANDOFF_P2.md` | 신규 | 이 문서 |

검증: `python -m py_compile` 전 파일 통과. ComfyUI 재시작 후 모델 인식 확인 완료.

---

## 7. 다음 PC에서 할 일 (우선순위)

| 순서 | 작업 | 파일 |
|---|---|---|
| 1 | 레포 clone → §3 스크립트로 모델/노드 설치 → ComfyUI executable 경로가 다르면 `Config.root`·`START_HINT` 수정 | `engine/config.py`, `engine/comfy.py` |
| 2 | `p2` CLI 서브커맨드 연결: `p2 make --image-model {krea2,qwen21,sdxl}`, `p2 env/check/verify` | `cli.py` (아직 미연결) |
| 3 | `engine/previs.py`: Blender 구조 전용 프리비즈 + depth/seg/bbox/pose/camera JSON 내보내기. `Scene3D`/`export_blender` 재사용 | `engine/layout3d.py` 참고 |
| 4 | `verify.py`에 facegate 통합 + contact sheet 육안 확인 절차 | `engine/verify.py` |
| 5 | 속도 최적화 후 1280×704 15초 pilot run (`p2-*`) 비교. 최종 합격은 **육안** | `docs/design/...md` §7 |
| 6 | 커밋·푸시 시 쉬운 설명 포함 유지 | — |

---

## 8. 함정 (꼭 기억)

| 함정 | 해결 |
|---|---|
| ComfyUI의 `unet_name`은 `distilled\` 접두어 포함, 파일시스템 경로는 `unet\distilled\` | `Config.ltx_dit_loader` / 파일 경로는 `m/"unet"/"distilled"/ltx_dit` 구분 사용 |
| ComfyUI 재시작 전엔 새 모델이 `object_info`에 안 보임 | 모델 설치 후 반드시 재시작 |
| `hf download` xet가 대용량에서 정체 | `HF_HUB_DISABLE_XET=1` (스크립트에 포함) |
| 두 다운로드 스크립트 동시 실행 시 `.lock` 대기 | 하나씩 실행 |
| 이미지 직접 열람은 이 모델에서 미지원 | 통계(Yavg 등) + 사람 육안 확인으로 판정 |
| Qwen-Image 2.1 = Qwen Research License(**비상업 전용**) | 상업 산출물은 기본값 Krea2 사용. Krea2 = Community License, 연매출 <$1M 무료 |
| 얼굴 유사도는 보조 지표 | 숫자 PASS만으로 합격 금지, contact sheet 육안 필수 |
