# P2 실사 이미지 모델 다운로드 (Krea 2 / Qwen-Image 2.1)
#
# 쉬운 설명:
#   - 3D는 영상의 틀만 잡습니다. 인물·소품·배경의 "사진 같은 외형"은
#     이 모델들로 만듭니다.
#   - Krea 2 : 사진 톤이 좋고 연매출 $1M 미만이면 무료 상업 사용 가능 (기본)
#   - Qwen-Image 2.1 : 참조 사진을 최대 10장까지 고정할 수 있지만
#                      라이선스가 연구·평가 전용이라 상업용으로는 쓰면 안 됩니다.
#   - 둘 다 12GB 그래픽카드에 맞춘 용량 줄인 버전을 받습니다.
#
# 사용: powershell -File tools/download_image_models.ps1

$ErrorActionPreference = "Stop"
$env:HF_HUB_DISABLE_XET = "1"

$HF = "C:\Users\mbc\AppData\Local\Python\pythoncore-3.12-64\Scripts\hf.exe"
$MODELS = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\models"
$STAGE = Join-Path $MODELS ".p2stage"
if (-not (Test-Path $STAGE)) { New-Item -ItemType Directory -Path $STAGE -Force | Out-Null }

function Get-Model {
    param([string]$Repo, [string]$File, [string]$Target)
    $dest = Join-Path $MODELS $Target
    if (Test-Path $dest) { Write-Host "[건너뜀] $Target" -ForegroundColor DarkGray; return }
    Write-Host "[$Repo] $File -> $Target" -ForegroundColor Cyan
    $dir = Split-Path $dest -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    & $HF download $Repo $File --local-dir $STAGE --quiet
    if ($LASTEXITCODE -ne 0) { throw "다운로드 실패: $Repo / $File" }
    $src = Join-Path $STAGE $File
    if (-not (Test-Path $src)) { throw "받은 파일을 못 찾음: $src" }
    Move-Item -LiteralPath $src -Destination $dest -Force
    Write-Host "[완료] $Target" -ForegroundColor Green
}

# ---- Krea 2 (기본) ----
# GGUF 포크(RealRebelAI/ComfyUI-GGUF_KREA-2) 설치 필요 — install_p2_nodes.ps1이 처리합니다.
Get-Model -Repo "realrebelai/KREA-2_GGUFs" `
    -File "TURBO/Krea-2-Turbo-Q5_K_S.gguf" `
    -Target "unet\Krea-2-Turbo-Q5_K_S.gguf"
Get-Model -Repo "Comfy-Org/Krea-2" `
    -File "text_encoders/qwen3vl_4b_fp8_scaled.safetensors" `
    -Target "text_encoders\qwen3vl_4b_fp8_scaled.safetensors"
Get-Model -Repo "Comfy-Org/Krea-2" `
    -File "vae/qwen_image_vae.safetensors" `
    -Target "vae\qwen_image_vae.safetensors"

# ---- Qwen-Image 2.1 (연구·평가 전용) ----
Get-Model -Repo "Comfy-Org/Qwen-Image-2.1" `
    -File "diffusion_models/qwen_image_2.1_int8_convrot.safetensors" `
    -Target "diffusion_models\qwen_image_2.1_int8_convrot.safetensors"
Get-Model -Repo "Comfy-Org/Qwen-Image-2.1" `
    -File "text_encoders/qwen3vl_8b_w4a8.safetensors" `
    -Target "text_encoders\qwen3vl_8b_w4a8.safetensors"
Get-Model -Repo "Comfy-Org/Qwen-Image-2.1" `
    -File "vae/qwen_image_2.1_vae_bf16.safetensors" `
    -Target "vae\qwen_image_2.1_vae_bf16.safetensors"
Get-Model -Repo "Comfy-Org/Qwen-Image-2.1" `
    -File "loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors" `
    -Target "loras\qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors"

Write-Host "실사 이미지 모델 다운로드 완료" -ForegroundColor Green
