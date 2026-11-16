# ENVIRONMENT — 로컬 실행 환경 (P0)

> 버전: v0.2 · 최초 작성: 2026-11-14 · 갱신: 2026-11-16
> 목적: 이 PC에 **무엇을, 어디에, 얼마나** 설치했고 **실측 성능이 얼마인지** 기록. 재설치·이전·문제해결의 유일한 기준.
> 관련: `DESIGN.md` D48(설치 권한) · D55(설치 경로) · D56(I2V 확정) · D57(생성 기본값) · PRD FR-18(모델·환경 관리)

---

## 0. 결론 (P0 통과 — 2026-11-16 사용자 육안 확인)

| P0 종료 조건 | 결과 | 근거 |
|---|---|---|
| **최종 5초 클립 (I2V)** | ✅ **사용자 확인 완료** | `output/p0/F_final_5s_crf16.mp4` (5.04s, 1280×704, 24fps, 4.67Mbps) |
| 키프레임 생성 | ✅ | `output/p0/kf_s202_00001_.png` (1280×704, 중앙 선명도 313.6) |
| 이미지→영상(I2V) 경로 | ✅ | F 생성 경로 그 자체 (D56으로 제품 경로 확정) |
| T2V (참고) | ⚠️ 동작하나 품질 낮음 | `output/p0/wan22_ti2v_5s_00001_.mp4` — 제품 경로에서 제외 |
| 오프라인 동작 | ✅ | 설치 후 외부 API 호출 없음 (모델 다운로드 시에만 네트워크) |

**판정: 이 PC(RTX 3060 12GB)에서 로컬 영상 생성이 제품에 쓸 수 있는 품질로 동작한다.**
사용자 육안 판정(2026-11-16): **"픽셀 안 깨지고 정상적"**.

**남은 한계(수용)**: 움직임이 보통(YDIF 2.98) · 5초 후반 디테일 15% 감소 · 영상 내 한글 렌더링 불가(자막은 FFmpeg 번인, FR-12).

---

## 1. 설치 위치 (레포 밖)

```
C:\Users\mbc\mokhwa\
├─ ComfyUI_windows_portable\   # 엔진 (4.55GB, 포터블)
│  ├─ python_embeded\          # 내장 Python (시스템 Python 미사용)
│  ├─ ComfyUI\
│  │  ├─ models\               # 모델 파일 (아래 §3)
│  │  ├─ input\                # I2V 입력 이미지
│  │  └─ output\p0\            # P0 테스트 산출물
│  ├─ tools\  (상위)           # 7zr.exe
│  └─ run_nvidia_gpu.bat
├─ tools\ffmpeg\               # FFmpeg 9.0.2 essentials
├─ workflows\                  # API 호출용 워크플로 JSON
├─ dl\                         # 다운로드 원본 (삭제 가능, ~2GB)
└─ logs\comfyui.log
```

- **git 저장소(`Documents\git\cinemokhwa`) 밖**에 둔다 → 30GB가 git 상태를 오염시키지 않음 (D55)
- 관리자 권한 불필요, 압축 해제만으로 동작 (D48)

---

## 2. 소프트웨어 버전

| 항목 | 버전 | 비고 |
|---|---|---|
| ComfyUI Portable (NVIDIA) | **0.45.0** | `ComfyUI_windows_portable_nvidia.7z` |
| └ SHA256 | `60c12e8c7af778047ad0413722dd3dc0f6ca773a41cbf5cb229ee9bc92c44a6f` | 검증 완료 |
| Python (내장) | 3.12 계열 | 시스템 Python 불필요 |
| PyTorch | **2.14.1+cu130** | CUDA 사용 가능 확인 |
| FFmpeg | 9.0.2 essentials | `tools\ffmpeg\...\bin\ffmpeg.exe` |
| 7-Zip standalone | 7zr.exe (602,624 B) | LZMA 7z 해제용 |
| GPU 드라이버 | 581.15 | RTX 3060 12GB |

---

## 3. 모델 (총 25.3GB)

| 파일 | 크기(byte) | 위치 (`ComfyUI/models/`) | 출처 |
|---|---|---|---|
| `wan2.2_ti2v_5B_fp16.safetensors` | 9,999,658,848 | `diffusion_models\` | `Comfy-Org/Wan-2.2` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6,735,906,897 | `text_encoders\` | 〃 |
| `wan2.2_vae.safetensors` | 1,409,400,960 | `vae\` | 〃 |
| `RealVisXL_V5.0_fp16.safetensors` | 6,938,065,488 | `checkpoints\` | `SG161222/RealVisXL_V5.0` |
| `RealESRGAN_x4.pth` | 67,040,989 | `upscale_models\` | `ai-forever/Real-ESRGAN` |

**미설치(2차)**: 애니 체크포인트(Animagine XL 계열), IPAdapter, LoRA. `D49` 카탈로그 확장 시 추가.

---

## 4. 실행 / 정지

```powershell
# 시작 (콘솔 없이)
C:\Users\mbc\mokhwa\ComfyUI_windows_portable\python_embeded\python.exe -s `
  "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\main.py" `
  --windows-standalone-build --disable-auto-launch --port 8188

# 상태 확인
Invoke-RestMethod http://127.0.0.1:8188/system_stats

# 정지
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*mokhwa*" } | Stop-Process
```

- 웹 UI: http://127.0.0.1:8188 (수동 실험용)
- 자동 API 호출용 워크플로: `workflows\p0_wan22_ti2v.json`, `p0_wan22_i2v.json`, `p0_sdxl_keyframe.json`

---

## 5. 실측 성능 (RTX 3060 12GB)

| 작업 | 설정 | 시간 | 비고 |
|---|---|---|---|
| 5초 T2V | 832×480 · 121f · 20 steps · fp8 | **342.79s** | 모델 로딩 포함 첫 실행 |
| 키프레임 SDXL | 832×480 · 28 steps | **24.86s** | RealVisXL |
| 키프레임 SDXL | 1280×704 · 32 steps | **24s** | RealVisXL, 2장째부터 |
| 5초 I2V | 832×480 · 121f · 20 steps · fp8 | **371s** (6.2분) | |
| 5초 I2V | 1280×704 · 121f · 20 steps · fp8 | **1080s** (18분) | 46.97s/step |
| **5초 I2V (최종)** | **1280×704 · 121f · 25 steps · fp8** | **1302s** (21.7분) | PNG 마스터 + CRF16 |

**확정 설정** (`workflows/` 참조)

```
Wan22ImageToVideoLatent  1280×704 · length 121 (4k+1)
UNETLoader              weight_dtype=fp8_e4m3fn
ModelSamplingSD3        shift=8.0          ← 필수. 빠지면 어둡고 정지된 영상
KSampler                uni_pc / simple · cfg 5 · steps 20~25
출력                    SaveImage(PNG 무손실) → FFmpeg CRF 16
```

**환산 (1280×704 I2V 20스텝 = 18분/5초 기준)**

| 완성 길이 | 클립 수 | 예상 시간 |
|---|---|---|
| 30초 | 6 | **약 1시간 50분** |
| 1분 | 12 | **약 3.6시간** |
| 3분 | 36 | **약 11시간** |

→ 저해상도(832×480)는 5.7분/5초로 2.8배 빠르지만 품질 손실 큼.
→ 1분 이상은 **야간 배치** 전제. PRD NFR-02 재산정 필요(§5.1).

### 5.1 품질 실측 (2026-11-16, 9회 생성)

동일 장면을 조건만 바꿔 측정. 지표: 밝기(YAVG), 대비, 세밀 디테일(고주파 성분), 프레임 간 변화(YDIF).

| 실험 | 경로 | 해상도 | 정밀도 | 스텝 | 밝기 | 대비 | 디테일 | 움직임 | 시간 |
|---|---|---|---|---|---|---|---|---|---|
| ① 원본 | T2V | 832×480 | fp8 | 20 | 91.0 | 42.7 | 8.78 | 0.98 | 5.7분 |
| ② | T2V | 1280×704 | fp16 | 30 | 28.9 | 13.9 | 1.42 | 1.11 | 11분 |
| ③ 공식설정 | T2V | 1280×704 | fp16 | 20 | 29.1 | 17.5 | 0.97 | 1.71 | 16분 |
| A 원본프롬프트 | T2V | 1280×704 | fp16 | 20 | 70.7 | 41.5 | 4.88 | 0.42 | 5.2분 |
| B 간판제거 | T2V | 1280×704 | fp16 | 20 | 34.4 | 40.7 | 1.84 | 3.30 | 5.3분 |
| C A와동일 | T2V | 1280×704 | fp8 | 20 | 71.7 | 42.2 | 4.72 | 0.40 | 5.5분 |
| D 새프롬프트 | T2V | 1280×704 | fp8 | 20 | 66.1 | 47.9 | 2.14 | 2.79 | 5.2분 |
| E | T2V | 1280×704 | fp8 | 20 | 63.7 | 32.8 | 2.71→1.48 | 1.09 | 18분 |
| E2 | T2V | 1280×704 | fp8 | 30 | 69.1 | 32.1 | 3.29→1.26 | 1.57 | 26분 |
| **F 최종** | **I2V** | **1280×704** | **fp8** | **25** | **76.1** | **44.4** | **2.53→1.97** | **2.98** | **21.7분** |

**검증된 결론**

| 후보 | 판정 | 근거 |
|---|---|---|
| 해상도 832→1280 | ❌ 원인 아님 | 1280에서도 동일하게 어두움 |
| fp16 ↔ fp8 | ❌ **차이 없음** | A 70.7/4.88 vs C 71.7/4.72. 속도도 동일(3060은 fp8 연산 유닛 없음) |
| 출력 압축(2.16Mbps) | ❌ 원인 아님 | PNG 3.29 vs CRF16 3.20 = **2.7% 차이** |
| `ModelSamplingSD3 shift=8` | ⭕ **필수** | 없으면 움직임 0.42 (정지 화면) |
| 프롬프트의 광원 | ⭕ **큼** | `neon signs` 제거 시 밝기 70.7→34.4 |
| **T2V vs I2V** | ⭕ **최대 요인** | I2V가 대비 +34%, 움직임 +90%, 피사체 선명도 유지 |

**I2V가 우수한 이유**: T2V는 노이즈에서 인물·조명·구도를 전부 발명해야 하지만, I2V는 선명한 SDXL 키프레임에서 시작해 **움직임만 생성**한다. 키프레임 선명도(중앙 313.5)를 영상이 263~288로 **약 85% 유지**하고, 5초 내내 안정적이다(T2V는 후반부 38%까지 열화).

**키프레임 자동 선택**: 시드 4종 생성(24초/장) 후 중앙 40% 선명도 최고를 선택. 측정값 229.1 / **313.6** / 262.2 / 261.6 중 선택. 비용 1.5분으로 품질 편차를 줄인다.

---

## 6. 설치 중 확인된 함정 (재설치 시 반복 금지)

| 함정 | 사실 | 대응 |
|---|---|---|
| Windows `tar.exe`로 7z 해제 | `LZMA codec is unsupported` | `7zr.exe` 사용 |
| Wan 5B fp8 체크포인트 | **없음** (fp16만 배포) | `UNETLoader`의 `weight_dtype=fp8_e4m3fn`으로 로드 시 변환 |
| 프레임 수 규격 | `length`는 **4k+1** (`121`=5.04s@24fps) | 24fps 기준 `5s→121`, `3s→73`, `10s→241` |
| I2V 입력 이미지 | `LoadImage`는 `ComfyUI/input\`만 읽음 | `output\`에서 복사 후 사용 |
| Real-ESRGAN 구 URL | GitHub v0.2.5.0 asset 404 | HuggingFace `ai-forever/Real-ESRGAN` 사용 |
| CLI 타입 | `CLIPLoader.type=wan` (소문자) | 대문자 아님 |
| VRAM | 12GB에 fp16(9.5GB) 적재 시 여유 부족 | fp8 로드 또는 해상도 하향 |
| **`ModelSamplingSD3` 누락** | shift 없이 돌리면 **어둡고 거의 정지된 영상**(YDIF 0.42) | `shift=8.0` 필수. 공식 템플릿 `video_wan2_2_5B_ti2v.json` 값 |
| **T2V로 품질 판정** | 제품 경로는 **I2V**. T2V는 노이즈에서 전부 발명 → 뭉개짐 | 품질 판정은 반드시 I2V로 |
| 프롬프트에서 광원 삭제 | 밤 장면에서 `neon signs` 제거 시 밝기 70.7→34.4 | `street lamps`·`lit shop windows`·`bokeh lights`로 대체 |
| `SaveVideo` 기본 모드 | `auto` = 압축 스트림 그대로 통과 | PNG 마스터(`SaveImage`) → FFmpeg `-crf 16` |
| 전역 선명도로 품질 판정 | 의도된 보케/심도 흐림을 "뭉개짐"으로 오판 | **중앙 40% 영역**을 따로 측정 |

---

## 7. 삭제 / 초기화

```powershell
Remove-Item "C:\Users\mbc\mokhwa" -Recurse -Force
```

레지스트리·서비스·시작프로그램을 건드리지 않으므로 **폴더 삭제가 곧 완전 제거**.

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v0.1 | 2026-11-14 | P0 코스 A 설치 완료 기록. ComfyUI 0.45.0 + Wan 2.2 TI2V-5B + RealVisXL + FFmpeg. 실측 성능·함정 정리 |
| v0.2 | 2026-11-16 | 품질 실측 9회 추가(§5.1). 확정 설정(shift=8·fp8·I2V·PNG마스터) 명시. 함정 5종 추가. I2V 1280×704 21.7분/5초 실측 |
