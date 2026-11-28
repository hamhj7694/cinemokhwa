# 신규 파이프라인 연구 — 정체성·구도 우선 하이브리드 (P2)

> **2026-11-26 상태:** 이 문서는 P2 방향의 기술 조사·가설·과거 계획 기록이다. **현재 통합 기준 문서는 [../P2_REQUIREMENTS.md](../P2_REQUIREMENTS.md)·[../P2_ARCHITECTURE.md](../P2_ARCHITECTURE.md)·[../P2_CONTRACTS.md](../P2_CONTRACTS.md)**. Layout-to-Render/LoRA/MSR/Blender 풀 프리비즈는 전체 통합 완료로 간주하지 않는다.

> 작성: 2026-11-21 · 개정: 2026-11-21 (3차) · 상태: **연구 완료 / 설치 진행 중**
> 2차 개정: **GGUF 경로 확정** (12GB 실행 가능) + 공식 **Layout-to-Render IC-LoRA** 발견 + **MSR V2 다중 참조** 채택
> 3차 개정: **3D는 틀만, 외형은 실사 이미지** (사용자 지적 반영) + **Krea 2 / Qwen-Image 2.1 드롭다운** 추가
> 배경: 사용자의 육안 판정 — *"지금도 다른 인물 같아. 지금 방식 그대로 하면 완성도 높은 영상 만들기는 어려울 거 같아. 일단 보류하고 다른 신규 파이프라인을 연구해보자!"*
> 사용자 제안 원문 — *"여러 객체나 인물이나 배경 요소를 핀 처럼 앵커하거나 고정하거나, ltx-2.5 사용하거나, 스테이블 디퓨전쓰거나, 블렌더로 풀 영상 구도 3d 모델링 먼저하고 그 위에 실사를 입히는 방식이나, 혹은 이러한 방식들을 혼합하는 방식으로 진행하자!!!!!!!!"*
> 결정: 기존 3D 가이드 파이프라인(D63~D72)은 **보류**. 신규 run ID는 `p2-*`.

---

## 2026-11-28 설계 보완 참고 — Adaptive Previs

기존 문서의 'Blender 풀 3D 프리비즈' 목표는 유지하지만, 실제 모델로 보여줄 3D 복잡도는 **샷별 최소 유효 정밀도**로 조절한다. 액션 샷에는 단순 root/camera proxy가 유리할 수 있지만 **신체 접촉/손동작**에 필요한 포즈·관절은 별도 데이터로 관리한다. 표정·실사 얼굴은 사진 참조와 영상 프롬프트 담당.
LTX는 `LTXVAddGuide` 희소 프레임 방식과 Layout-to-Render 전체 비디오 IC-LoRA가 다르며, 전자는 전체 3D 움직임 고정을 보장하지 않는다.
**현행 규범:** [ADAPTIVE_PREVIS](ADAPTIVE_PREVIS.md) · [실험 계획](../experiments/P2_PREVIS_VALIDATION.md) · [결정 기록](../adr/ADR-001-adaptive-previs.md). 아래 2026-11-21 연구 기록은 개발 완료로 해석 금지.

## 1. 결론 먼저 — 제안 5축 통합

기존 방식은 **"씬마다 얼굴을 새로 생성하고, 약한 참조로 보정한다"**는 구조였다.
생성 횟수만큼 정체성 표본이 생기므로 드리프트가 구조적으로 불가피했다.
파라미터 tuning이 아니라 **정체성과 구도를 누가 소유하는지**를 바꿔야 한다.

사용자가 제안한 5개 축은 서로 경쟁하는 대안이 아니라 **서로 다른 계층을 담당하는 조각**이다.
아래처럼 배치하면 각 축의 약점이 다른 축의 강점으로 메워진다.

| 사용자 제안 | 기술적 해석 | 담당 계층 | 핵심 근거 |
|---|---|---|---|
| ① 핀/앵커/고정 | 프레임·객체 단위 참조 고정 | L2·L3 | LTX `--image PATH FRAME_IDX STRENGTH` + **MSR V2 슬롯 임베딩(최대 5개)** + FL-Path Point Tool + Blender 객체 ID |
| ② LTX-2.5 | 22B 영상 모델, **native multishot**, GGUF 양자화 | L3 영상화 | 컷을 넘어 인물·환경·조명 유지 = scene 2 해독제. **UD-Q3_K_XL 12GB로 3060 실행** |
| ③ Stable Diffusion | SDXL 캐릭터 LoRA + ControlNet | L0·L2 | 정체성의 단일 원본을 가중치에 새김. 실사 질감 담당 |
| ④ Blender 풀 3D → 실사 입히기 | 15초 전체 프리비즈를 3D로 확정 후 렌더 위에 생성 | L1·L3 | **공식 Layout-to-Render IC-LoRA**가 클레이 영상 → 실사 샷을 그대로 수행 |
| ⑤ 혼합 | 위 4개를 계층으로 결합 | 전체 | 단일 모델로는 VRAM·정체성·구도를 동시에 못 잡음 |

> 한 줄 요약: **Blender가 "어디에 무엇이 있는지"를 15초 내내 지배하고, SDXL이 "누구인지"를 지배하고, LTX-2.5가 "어떻게 움직이는지"를 담당한다.**

---

## 2. 진단 — 왜 다른 사람인가 (실측)

`tools/face_identity.py` (OpenCV Zoo YuNet+SFace, Apache 2.0, CPU)로 측정.
SFace 코사인 판정 경계는 약 **0.36**(이하면 타인).

| 측정 대상 | 유사도 | 판정 |
|---|---|---|
| guided-50 scene 1 키프레임 ↔ 카드 | 0.6308 | 사촌 수준 |
| guided-50 scene 2 키프레임 ↔ 카드 | **0.3559** | **타인** |
| guided-50 scene 3 키프레임 ↔ 카드 | 0.6737 | 사촌~본인 |
| scene 1 키프레임 ↔ scene 2 키프레임 | **0.2572** | **완전히 다른 사람** |
| scene 1 키프레임 ↔ scene 3 키프레임 | 0.6771 | 닮음 |

> 사용자가 처음 한 말 — *"1,3 프레임이 닮은 사람 같고, 2번은 다르다"* — 과 **정확히 일치**한다.

### 원인 3가지

| # | 원인 | 근거 | 기존 설계와의 관계 |
|---|---|---|---|
| A | **scene 2는 정체성 참조가 아예 없음** | `state.json`: scene 2 `reference=''`, `reference_mode='none'` | D63에서 연장 씬의 레이아웃 주입을 끄면서 참조도 함께 끊김. 체이닝이 얼굴까지 유지한다고 가정했으나 틀림 |
| B | **I2V 체이닝 중 정체성 희석** | scene 2 프레임 0.619 → 0.520 (끝으로 갈수록 감소) | 121프레임 단일 생성에 참조 재주입 없음 |
| C | **IPAdapter 자체가 약함** | 최고 0.674. 공개 벤치: IPAdapter ~0.62 / PuLID ~0.69 / InstantID ~0.78 / 학습 LoRA 최상 | CLIP-Vision 임베딩은 "닮은 그림"을 만들지 "그 사람"을 만들지 않음 |

### 기존 verify가 왜 못 잡았나

`verify.py`는 밝기·선명도·이음새·팔레트만 본다. **얼굴을 전혀 안 본다.**
그래서 사용자 눈에는 "다른 사람"인데 숫자는 WARN/PASS였다. D71~D72로 밝기를 고쳐도
같은 불만이 반복된 것은 당연하다. → **신규 파이프라인에는 얼굴 게이트가 필수.**

---

## 3. 구성요소 조사 결과 (로컬 제약 반영)

환경: **RTX 3060 12GB**, ComfyUI embedded Python 3.13, Blender 4.5.16 LTS, 전부 오프라인·무료.

### 3.1 LTX-2.5 — 공식 문서 실측 (2026-11-21 확인)

| 항목 | 확인된 사실 | 우리에게 의미 |
|---|---|---|
| 라이선스 | **LTX-2.x Community License** (2026-08-11 제정, 2026-11-11 개정). 연매출 **$10M 미만** 무료 상업 사용. 이상은 유료 계약 | 개인/소규모 프로젝트는 무료. 단 파인튜닝 이전(transfer)은 유료 가능 |
| 구조 | 22B DiT 분할 safetensors + **Gemma4 12B** 텍스트 인코더 + Video/ Audio VAE + spatial/temporal x2 업스케일러 | 컴포넌트별 로딩. 텍스트 인코더도 12B → VRAM 계산에 포함해야 함 |
| 증류 모델 | distilled DiT: **고정 8스텝, CFG=1** | 20스텝 요구사항보다 빠름. 품질은 dev-transformer + distilled LoRA로 보완 |
| **저VRAM 공식 옵션** | `--quantization fp8-cast --offload cpu`. **그리고 GGUF 양자화가 더 현실적** | `ComfyUI-GGUF`의 `Unet Loader (GGUF)`로 UD-Q3_K_XL(12GB) 사용 확정 |
| 사용 불가 양자화 | `nvfp4`는 **Blackwell 전용** → 3060 불가. `comfy-int8-convrot`는 ComfyUI 전용 | 우리 경로는 **GGUF**. bf16 원본(39GB)은 받지 않음 |
| **GGUF 실측(Unsloth)** | distilled `UD-Q3_K_XL` 12.00GB / LPIPS 0.310 / PSNR 19.1dB. **UD-Q2_K_XL 9.5GB**도 LPIPS 0.416. 공식 샘플이 **1280×704·121프레임·24fps** | 우리 목표 해상도와 동일 조건으로 검증된 조합. 12GB에 딱 맞음 |
| 텍스트 인코더 GGUF | Gemma4 12B `Q4_K_M` 7.84GB (원본 bf16 24.46GB) | `CLIPLoader (GGUF)`로 로드. 다운로드·VRAM 3배 절감 |
| **멀티 앵커** | `--image PATH FRAME_IDX STRENGTH` 를 **여러 번** 지정. frame 0 = 첫 프레임, `-1`도 사용 | 객체/인물/배경을 프레임별로 핀하는 기능이 모델에 이미 있음 |
| **Native multishot** | 한 패스에서 연결된 여러 샷. 인물·환경·조명·목소리·스타일 **컷 간 유지** | scene 2 이탈 문제에 대한 직접 해독제 |
| 제약 | `num_frames % 8 == 1` (1, 9, …, 49, 121), width/height **32 배수** (Layout-to-Render는 64 배수) | 121프레임 ✅. **1280×704는 32배수(40×22)이자 64배수(20×11)** → 두 파이프라인 모두 그대로 사용 가능 |
| 파인튜닝 | dev transformer 학습 가능, `ltx-trainer`. LTX-2.3 LoRA 대부분 호환 | 캐릭터 LoRA를 LTX에 직접 새기는 것도 가능(업그레이드 경로) |
| **공식 IC-LoRA** | **Layout-to-Render**(1.22GB): Blender/Unreal 클레이·블로킹 영상 + 첫 프레임 → 실사. **Stage1 960×544 8스텝 → Stage2 1920×1088 3스텝** | 사용자 제안 ④의 공식 구현. 우리 파이프라인의 핵심 엔진으로 채택 |
| **공식 Ingredients IC-LoRA** | 멀티 서브젝트 참조, 1.22GB | 다중 인물 확장 후보 |
| **Licon MSR V2** | **Apache 2.0**, 2.06GB. 최대 **5개 참조 이미지**를 슬롯 임베딩 + 고유 시간 위치로 고정 | 사용자 제안 ①의 직접 구현. 다중 인물/소품 앵커로 채택 |

> 결론: LTX-2.5는 **GGUF + ComfyUI로 12GB에서 실행 가능**하다. 22B bf16을 억지로 올리는 게 아니라
> 검증된 양자화 경로(UD-Q3_K_XL 12GB + 텍스트 인코더 Q4_K_M 7.8GB)를 쓴다.
> 남은 리스크는 **속도**(15초 ≤70분)뿐이며, §7에 대안을 명시했다.

### 3.2 핀/앵커 구현 옵션

| 옵션 | 라이선스 | 고정 단위 | 12GB | 채택 |
|---|---|---|---|---|
| **Licon MSR V2** | **Apache 2.0** (어댑터) | 최대 5개 참조 이미지, 슬롯 임베딩 + 고유 시간 위치, 오디오 2명 | GGUF와 함께 사용 | **1순위** — 다중 인물/사물 고정의 직접 구현 |
| **LTX-2.5 `--image PATH FRAME_IDX STRENGTH`** | LTX-2.x | 프레임 인덱스 + 강도, 여러 번 지정 가능 | GGUF 경로 | **2순위** — 모델 네이티브 프레임 앵커 |
| **ComfyUI_FL-Path-Animator** (MIT) | MIT | Point Tool = 정적 앵커, Lock Perimeter = 테두리 고정, 121점 리샘플, IMAGE+MASK+STRING 출력 | ✅ 가벼움 | **3순위** — 2D 앵커/마스크 생성기 |
| **Blender 객체 ID + bbox/depth** | GPL(도구) | 3D 객체 단위. Object Index Pass가 instance mask 제공 | ✅ | 앵커의 "원본 좌표" |
| MiniMaxH3AddGuide 계열 | 확인 필요 | frame_idx 가이드 | 미검증 | 조사 중 |

> FL-Path의 121점 리샘플·정적 점 반복 아이디어는 **"앵커는 흔들리면 안 된다"**는 우리 요구와 정확히 같다.
> 다만 이 노드는 *형체遮mask*를 만들 뿐 얼굴 정체성은 못 만든다 → SDXL LoRA와 조합해야 함.

### 3.3 Blender 풀 3D → 실사 입히기 (BlenderFusion 원칙)

Google DeepMind의 BlenderFusion(arXiv:2506.17450) 파이프라인에서 차용할 부분:

| 단계 | 논문 방식 | 우리 적용 |
|---|---|---|
| Layering | SAM2 마스크 + Depth Pro 깊이 → 3D 메시 리프트 | MakeHuman/MPFB CC0 인물 + 단순 세트 메시를 **처음부터 3D로 배치**(리프트 불필요) |
| Editing | Blender에서 객체/카메라 변형 | 15초 전체 카메라·인물·소품·배경을 **프리비즈로 키프레이밍** |
| 조건 생성 | Object Index Pass = instance mask, Plücker 카메라 임베딩, 3D bbox | depth / seg / bbox / pose PNG+JSON을 전 프레임 내보내기 |
| Compositing | dual-stream SD2.1이 Blender 렌더 위에 실사 텍스처 생성 | **SDXL ControlNet + LTX-2.5 I2V**가 같은 역할. 학습은 안 함 |

> 논문은 8×A100 80GB로 30k step 학습했으므로 **우리가 모델을 재학습할 수는 없다.**
> 하지만 "정확한 제어는 Blender가, 사실감은 생성 모델이"라는 **역할 분리 원칙은 그대로 쓸 수 있다.**
> VerseCrafter(TencentARC)도 Blender 전처리 → point cloud → video diffusion 순서를 쓴다. 같은 방향.

### 3.4 역할 재정의 — 3D는 "틀", 실사 이미지가 "외형" (3차 개정)

> **사용자 지적(2026-11-21):**
> *"3d로 영상의 틀만 잡고, 그 위에 인물이나 물품, 사물, 배경은 실사 혹은 아주 실사적이고
> ai티 안나는 ai 생성이미지사진을 모티브로 해야하는 거 아니야? 내가 잘 못 이해했나?"*
>
> **→ 맞습니다. 2차 개정의 L0이 모순돼 있었습니다.** 3D 렌더를 LoRA 학습 데이터로 쓰면
> 모델은 3D 재질·조명 톤을 "정체성"으로 배웁니다. 3D는 **구조만**, 실사는 **외형만** 담당하게 고칩니다.

| 요소 | 2차 개정 (잘못됨) | **3차 개정 (정정)** |
|---|---|---|
| 3D 렌더 역할 | LoRA 학습 데이터 = 정체성 원본 | **오직 틀**: 카메라 경로, 객체 위치, 깊이/분할/bbox/포즈 |
| 실사 이미지 역할 | 키프레임 결과물일 뿐 | **외형·정체성·질감의 유일한 원본** |
| LoRA 학습 데이터 | 3D 다각도 렌더 24장 | **실사 AI 사진 24장**(동일 인물, 3D 포즈를 조건으로 생성) |
| 다각도 확보 방법 | 3D 모델 회전 렌더 | 3D가 포즈·각도를 지정 → 실사 모델이 그 포즈의 사람을 생성 |
| 배경·소품 | 3D 메시 색상 | 3D는 위치만, 실제 질감은 실사 생성 이미지를 콜라주/합성 |

| 기존 | 신규 |
|---|---|
| 참조 이미지 → IPAdapter로 매 씬 얼굴 흉내 | **실사 기준 사진 + LoRA**가 정체성 소유. 3D는 얼굴을 만들지 않음 |
| SDXL만 사용 | **Krea 2 / Qwen-Image 2.1 / SDXL** 중 드롭다운 선택 |
| 키프레임 품질만 담당 | 키프레임 + 3D 조건(depth/pose/seg) + 실사 질감 담당 |
| 참조가 끊기면 타인 | 가중치와 앵커가 고정 → 구조적 동일성 |

> PuLID/InstantID는 InsightFace(비상업) 의존으로 제외.
> 학습 LoRA가 공개 비교에서 1위지만, **학습 재료는 반드시 실사 이미지**여야 한다.

### 3.6 실사 이미지 모델 드롭다운 (사용자 요청)

CLI `p2 make --image-model {krea2,qwen21,sdxl}` / `Config.image_model` / UI 드롭다운으로 전환한다.
기본값은 **Krea 2**(상업 가능 + 사진 톤). Qwen-Image 2.1은 성능은 좋지만 **라이선스 주의**.

| 모델 | ComfyUI 노드 | 12GB 구성 | 스텝 | 라이선스 | 역할 |
|---|---|---|---|---|---|
| **Krea 2 (기본)** | `UNETLoader`(GGUF fork) + `CLIPLoader type=krea2` + `VAELoader` | DiT GGUF Q5_K_S 8.2GB + TE fp8 4.9GB + VAE 0.2GB | Turbo 8 | **Krea-2 Community**: 연매출 <$1M 무료 상업, 이상은 Enterprise | 사진 같은 피부·질감, 인물/소품/배경 기준 사진 |
| **Qwen-Image 2.1** | `UNETLoader` + `CLIPLoader type=qwen_image` + `VAELoader` | int8_convrot 6.8GB + TE w4a8 5.9GB + VAE 0.6GB | Turbo LoRA 5~8 | **⚠ Qwen Research License: 비상업(연구·평가) 전용**. 상업 실행 시 별도 라이선스 필요 | 최대 10장 참조로 인물/제품 정체성 보존, 사실적 텍스처·조명 |
| SDXL (레거시) | 기존 `checkpoint` + IPAdapter | RealVisXL 6.5GB | 32 | 기존 사용 중 | 이전 파이프라인 호환용 |

> **AI 티 방지 공통 프롬프트 규칙**: `photorealistic, shot on Sony A7R V, 85mm f/1.8, natural skin
> pores, subtle film grain, real-world lighting, no illustration, no 3d render, no plastic skin`
> 네거티브: `3d render, CGI, cartoon, anime, plastic, oversaturated, airbrushed, AI artifact`.

생성한 이미지는 `face_identity.py` 게이트(≥0.60)와 **육안 확인**을 모두 통과해야 앵커 뱅크에 저장된다.

### 3.5 12GB 실행 구성 확정 (다운로드 진행 중)

| 컴포넌트 | 파일 | 크기 | 설치 위치 |
|---|---|---|---|
| distilled DiT | `unsloth/LTX-2.5-GGUF` → `ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf` | 12.00 GB | `models/unet/` |
| 텍스트 인코더 | `joeygambino/LTX-2.5-Quantized` → `gemma4-12b-ltx25-comfy-w4a8.safetensors` | 9.88 GB | `models/text_encoders/` |
| 영상 VAE | `ltx-2.5-video-vae-conv-bf16.safetensors` | 1.35 GB | `models/vae/` |
| 오디오 VAE | `ltx-2.5-audio-vae-bf16.safetensors` | 0.34 GB | `models/vae/` |
| 공간 업스케일러 | `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` | 0.93 GB | `models/latent_upscale_models/` |
| 레이아웃→실사 | `Lightricks/...Layout-To-Render...1.0.safetensors` | 1.22 GB | `models/loras/` |
| 다중 참조 | `LTX-2.5-Licon-MSR-V2.safetensors` | 2.06 GB | `models/loras/` |
| **합계** | | **≈ 25.7 GB** | 디스크 여유 302 GB ✅ |

설치 스크립트: `tools/download_p2_models.ps1`, `tools/install_p2_nodes.ps1`.
커스텀 노드 4종(ComfyUI-GGUF / ComfyUI-LTXVideo / ComfyUI-LTX2.5-MSR / ComfyUI_FL-Path-Animator) 설치 완료.

> TE는 **GGUF로 없음**(ComfyUI-GGUF의 `TXT_ARCH_LIST`에 `gemma3`만 있고 `gemma4`는 없음).
> 공식 README도 *"No GGUF of the LTX-2.5 encoder exists"*라고 명시 → `CLIPLoader(type=ltxv)` + w4a8 safetensors로 확정.
> speed-down 대비: DiT를 `UD-Q2_K_XL`(8.9GB)로 교체하면 2.3GB 절약, 품질은 소폭 하락. OOM 시 즉시 전환 가능하도록 함께 받는다.

---

## 4. 추천 설계 — 5계층 Hybrid Identity-First

```
[L0] 정체성 원본 (1회, 영구 자산 — M-B/M-C 공통)     ← 외형은 실사만
   실사 기준 사진 1장(카드) + 3D 포즈 가이드 24~32개
                     ↓ Krea 2 / Qwen-Image 2.1 (드롭다운)
   같은 사람의 실사 사진 24~32장 (AI 티 제거 프롬프트 + 얼굴 게이트)
                     ↓ kohya_ss (12GB, batch1·dim32·bf16·8bit Adam)
              char_jun.safetensors  ← "누구인지"의 단일 진실 원본
                     ↓
   앵커 뱅크: 실사 카드/프로필/의상/표정 컷 PNG (프레임 앵커 재료)
   ※ 3D는 포즈·각도 지정용으로만 쓰이고 학습 데이터에는 안 들어감

[L1] Blender 풀 3D 구도 (씬별, 15초 전체 프리비즈)   ← 사용자 제안 ④
   카메라 무빙·인물·소품·배경의 "위치와 움직임만" 3D로 배치
   전 프레임(361프레임)에서 depth + instance seg + 2D/3D bbox + pose + camera json 추출
   → 각 객체에 고정 ID = "핀/앵커"의 좌표. 색·재질·외형은 만들지 않음

[L2] 실사 키프레임 (샷별 대표 프레임)                 ← 사용자 제안 ③
   모델 드롭다운: krea2(기본) | qwen21 | sdxl
   실사 기준 앵커 + L1의 depth/pose 조건으로 인물·소품·배경 생성
                     ↓  얼굴 게이트(>=0.60) + 육안 확인 통과한 것만 채택
   → 실사 키프레임 = LTX 앵커로 쓸 이미지 (3D 톤이 섞이지 않음)

[L3] LTX-2.5 영상화 + 프레임 앵커                    ← 사용자 제안 ①②
   ComfyUI-GGUF: UD-Q3_K_XL DiT + Gemma4 w4a8 TE
   + 공식 Layout-to-Render IC-LoRA(1.0) ← L1 클레이 영상이 구도 지배 (제안 ④의 완성)
   + Licon MSR V2 ← 인물/소품/배경 최대 5개를 슬롯으로 핀 (제안 ①의 완성)
   + --image first.png -1 1.0 / mid.png 36 1.0 / last.png 72 1.0  (화면 고정)
   + native multishot로 3씬 연결, 1280×704 · 121프레임 · 24fps
   + FL-Path 앵커 마스크는 실험 옵션

[L4] 검증 — 얼굴 최우선
   face_identity.py로 매 씬 대표 프레임 측정 → 미달 시 FAIL
   밝기/선명도 검사는 보조 지표. 마지막은 사람 눈으로 확인 (숫자 PASS만으로 통과 불가)
```

### 계층별 설계 근거

| 계층 | 왜 이렇게 하나 | 제안 축 |
|---|---|---|
| L0 실사 → 데이터셋 | 3D 렌더를 학습에 쓰면 **3D 톤을 정체성으로 배운다**. 실사 기준 사진에서 출발해 3D가 포즈만 지정한 실사 사진 24장을 만들고, 얼굴 게이트로 걸러야 진짜 같은 사람이 된다 | ③ |
| L0 앵커 뱅크 | 프레임 앵커로 넣을 이미지를 미리 확정. 생성 중 즉흥적으로 고르지 않음 | ① |
| L1 풀 3D = 틀만 | "씬마다 새로 생성"을 없앤다. 구도·위치·카메라가 15초 내내 **수치로 고정**됨. 이게 진짜 핀. **3D는 색·재질·얼굴을 만들지 않는다** | ④⑤ |
| L1 조건 출력 | depth/seg/bbox가 ControlNet과 LTX 조건의 입력 → Blender가 생성 모델을 "지배" | ④⑤ |
| L2 모델 드롭다운 | Krea 2(사진 톤·상업 가능) / Qwen-Image 2.1(참조 10장·비상업) / SDXL(레거시)을 `--image-model`로 전환 | ③ |
| L2 LoRA 고정 | 시드마다 다른 얼굴이 나오던 문제가 사라짐. 학습 재료는 **실사 사진**이어야 3D 톤이 안 배임 | ③ |
| L2 3D 조건 주입 | 실사 키프레임도 L1의 depth/pose를 따름 → 키프레임과 영상 구도가 어긋나지 않음 | ③④ |
| L3 Layout-to-Render | Blender 클레이 영상이 카메라·사물 위치를 지배. 첫 프레임이 색·조명·재질을 지정 → **별도 ControlNet 학습 불필요** | ④⑤ |
| L3 MSR V2 슬롯 | scene 2의 0.619→0.520 드리프트는 참조 희석. 참조를 슬롯으로 고정해 경계마다 되돌림 | ① |
| L3 multishot | 컷을 넘어 정체성 유지. 기존 D63 참조 차단 문제를 모델 수준에서 해결 | ② |
| L4 얼굴 게이트 | 사용자 육안 불만을 자동 검증 대상으로 승격 | 전체 |

### M-B / M-C 확장 시 재사용되는 공통 레이어

| 공통 자산 | M-B | M-C |
|---|---|---|
| `char_jun.safetensors` (L0 LoRA) | 그대로 | 그대로 |
| 앵커 뱅크 (L0) | 그대로 + 표정 추가 | 그대로 |
| 3D 인물 메시 / 세트 템플릿 (L1) | 카메라·조명만 변경 | 카메라·조명만 변경 |
| depth/seg 내보내기 스크립트 | 공통 | 공통 |
| face_identity 게이트 임계값 | 공통 | 공통 |
| 프롬프트/사운드/컷 구성 | 새로 작성 | 새로 작성 |

> 즉 B·C는 **"새 얼굴을 만들지 않고"** 카메라·프롬프트·사운드만 바꿔서 만든다.

---

## 5. 실행 계획

| 단계 | 작업 | 산출물 | 상태 |
|---|---|---|---|
| 0 | 얼굴 유사도 측정 도구 + 실측 진단 + 5축 조사 | `tools/face_identity.py`, 본 문서 | ✅ 완료 |
| 1 | MPFB 설치 + 인물 3D 모델 + 다각도 렌더 24장 + 앵커 뱅크 | `assets/char_jun/views/*.png` | ⏳ 다음 |
| 2 | kohya_ss로 SDXL LoRA 학습 (dim32, ~1~2시간) | `models/lora/char_jun.safetensors` | ⏳ |
| 3 | Blender 풀 3D 15초 프리비즈 + depth/seg/bbox/pose 내보내기 | `engine/layout3d.py` 확장, `p2-pilot/previs/` | ⏳ |
| 4 | SDXL + ControlNet 실사 키프레임, 얼굴 게이트 적용 | `p2-pilot/keyframes/` | ⏳ |
| 5 | LTX-2.5 GGUF + Layout-to-Render + MSR V2 프로토타입 (짧은 클립으로 속도 실측) | `engine/animate.py` | ⏳ |
| 6 | 얼굴 게이트 `verify.py` 통합, 기존 파이프라인과 비교 | `p2-pilot/metrics.json` | ⏳ |

> 기존 `guided-50`은 **보류 상태로 보존**. 재개 지시 전까지 기존 파이프라인을 수정하지 않는다.

---

## 6. 라이선스 매트릭스 (2026-11-21 확인 기준)

| 구성요소 | 라이선스 | 비고 |
|---|---|---|
| Blender 4.5.16 LTS | GPL | 설치 완료 |
| MakeHuman community assets | **CC0** | 인물 메시·의상·포즈, 상업 가능 |
| MPFB (Blender 플러그인) | GPLv3 | 플러그인 코드. 생성 결과물은 별도 |
| OpenCV + YuNet/SFace | **Apache 2.0** | 얼굴 검출·인식, 설치 완료 |
| ComfyUI_FL-Path-Animator | **MIT** | 앵커 마스크 생성기 |
| **LTX-2.5 가중치 / GGUF / IC-LoRA** | **LTX-2.x Community License** | 연매출 $10M 미만 무료. 파인튜닝 이전은 유료 가능. **GGUF는 비공식 양자화 파생물이지만 동일 라이선스** |
| Licon MSR V2 어댑터 | **Apache 2.0** | 다중 참조. 단, 기반 LTX 가중치는 위 라이선스 |
| LTX-2 Apache Code | Apache 2.0 | 추론·학습 코드. 가중치는 별도 계약 |
| SDXL / RealVisXL V5 | 기존 사용 중 | 계속 확인 필요 |
| Krea 2 | Krea-2 Community License | 연매출 <$1M 무료 상업. 이상은 Enterprise 별도 계약 |
| Qwen-Image 2.1 | **Qwen Research License** | **비상업(연구·평가) 전용.** 상업 사용 시 별도 라이선스 필요 |
| FLUX.2 klein 4B | Apache 2.0 | 13GB → 12GB에서 양자화 검토 (예비) |
| InsightFace antelopev2 | **비상업 연구용** | 회피 |
| InstantID 체크포인트 | **비상업 연구용** | 미설치 |
| Wan-Animate-2 / Stand-In (14B) | Apache 2.0 | 24GB+ → 보류 |

> 원칙: D69에서처럼 상업 제약이 있는 가중치는 설치하지 않는다.
> LTX-2.x Community License는 **매출 조건부 무료**이지 완전 자유(Public Domain)가 아님을 명시한다.

---

## 7. 열린 질문 / 리스크

| 항목 | 내용 | 대안 |
|---|---|---|
| **12GB + 22B 속도 — 실측 완료** | GGUF Q3 + 960×544 + **25프레임 530초**. 121프레임 환산 **42.8분**, 15초(3클립) **128분** → 목표 70분 **미달**. OOM은 없었음 | ① 스테이지 해상도를 960×544→768×432로 낮추면 픽셀 0.64배 → 82분. ② Q2(8.9GB)로 교체 → 추가 단축. ③ **25프레임 세그먼트 5~6개 + 8스텝 sigmas 유지**가 가장 확실. 최종 1280×704는 VAE decoder 타일링 후 upscale 스테이지에서 처리 |
| 텍스트 인코더 12B | GGUF Q4_K_M(7.8GB)로 다운로드·VRAM 해결. 로딩 후 CPU 오프로드 가능 | Q2_K(5.55GB)로 추가 절감 가능 |
| 데이터셋 품질 | 3D 렌더를 학습에 쓰면 LoRA가 3D 톤을 배움 | **3D는 포즈만**, 학습 이미지는 실사 생성 사진으로 구성 (3차 개정 반영) |
| AI 티 / 실사감 | 모델 기본 프롬프트로는 플라스틱 피부·과채도가 나올 수 있음 | 사진 렌즈·필름 그레인·모공 프롬프트 + 네거티브 적용, **육안 게이트 필수** |
| Qwen-Image 2.1 라이선스 | Qwen Research License는 **비상업 전용** | 기본값은 Krea 2. Qwen은 연구·평가용으로만 실행하고 상업 산출물에 쓰지 않음 |
| LoRA 과적합 | 표정/각도 고정 → 자연스러움 저하 | dim 32 / 15 epoch / 다양한 각도 |
| 세그먼트 앵커 이음새 | 앵커 재주입 경계에서 깜빡임 가능 | D72의 yavg_step_ratio로 모니터 |
| 멀티 서브젝트 | MSR V2(Apache 2.0)가 최대 5개 슬롯을 지원하지만 우리 장면에서의 안정성은 미검증 | 단일 인물 먼저 검증 후 2→5개로 확장 |
| 측정 임계값 | SFace 0.36 = 타인 경계. 게이트 통과선 0.60으로 시작 | 파일럿 데이터로 보정 |
| **육안 게이트** | 이 모델은 이미지를 직접 판정 못 함 | 최종 합격은 사용자가 눈으로 확인. 숫자 PASS만으로 통과 불가 원칙 유지 |

---

## 8. 참고 출처

| 출처 | URL |
|---|---|
| LTX-2.5 모델 카드 (스펙·저VRAM 옵션·멀티 앵커·제약) | https://huggingface.co/Lightricks/LTX-2.5 |
| LTX-2.x Community License 원문 | https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x |
| LTX character consistency 공식 블로그 | https://ltx.io/blog/how-to-maintain-character-consistency-in-ai-video |
| ComfyUI_FL-Path-Animator (Point Tool / MIT) | https://github.com/filliptm/ComfyUI_FL-Path-Animator |
| BlenderFusion (3D-Grounded Editing and Generative Compositing) | https://arxiv.org/html/2506.17450v2 |
| VerseCrafter Blender 전처리 | https://github.com/TencentARC/VerseCrafter/blob/main/README_BLENDER.md |
| POCI-Diff (3D bbox + 텍스트 바인딩) | https://arxiv.org/html/2601.14056v1 |
| OpenCV Zoo YuNet / SFace | https://github.com/opencv/opencv_zoo |
| LTX-2.5 GGUF (UD-Q3_K_XL 12GB, 1280×704 샘플) | https://huggingface.co/unsloth/LTX-2.5-GGUF |
| Gemma4 12B GGUF 텍스트 인코더 | https://huggingface.co/elix3r/gemma4-12b-with-proj-ltx-2.5-GGUF |
| **공식 Layout-to-Render IC-LoRA** | https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render |
| Licon MSR V2 (다중 참조, Apache 2.0) | https://huggingface.co/LiconStudio/LTX-2.5-Multiple-Subject-Reference |
| ComfyUI-GGUF / ComfyUI-LTXVideo | https://github.com/city96/ComfyUI-GGUF · https://github.com/Lightricks/ComfyUI-LTXVideo |
