# P2 하이브리드 파이프라인용 모델 다운로드 (전부 무료 / 로컬)
#
# 쉬운 설명:
#   - LTX-2.5 영상 모델을 우리 컴퓨터(12GB 그래픽카드)에서 돌릴 수 있게
#     용량을 줄인 버전(GGUF)을 받습니다.
#   - 블렌더로 만든 3D 구도를 실사 영상으로 바꿔주는 공식 부품과,
#     여러 인물을 각각 고정해 주는 부품도 함께 받습니다.
#
# 사용: powershell -File tools/download_p2_models.ps1
# 다시 실행해도 이미 받은 파일은 이어서 받습니다(재다운로드 안 함).

$ErrorActionPreference = "Stop"

$HF = "C:\Users\mbc\AppData\Local\Python\pythoncore-3.12-64\Scripts\hf.exe"
$MODELS = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\models"

function Get-Model {
    param(
        [string]$Repo,
        [string]$File,
        [string]$Subdir
    )
    $dest = Join-Path $MODELS $Subdir
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    Write-Host "[$Repo] $File -> $Subdir" -ForegroundColor Cyan
    & $HF download $Repo $File --local-dir $dest --quiet
    if ($LASTEXITCODE -ne 0) { throw "다운로드 실패: $Repo / $File" }
}

# 1) LTX-2.5 distilled DiT — GGUF UD-Q3_K_XL (약 12GB, 12GB 카드용 균형점)
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "distilled/ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf" -Subdir "unet"

# 2) Gemma4 12B 텍스트 인코더 — GGUF Q4_K_M (약 7.8GB)
Get-Model -Repo "elix3r/gemma4-12b-with-proj-ltx-2.5-GGUF" `
    -File "gemma4-12b-with-proj-ltx-2.5-Q4_K_M.gguf" -Subdir "text_encoders"

# 3) 영상/오디오 VAE + 2배 업스케일러 (작은 파일)
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "vae/ltx-2.5-video-vae-conv-bf16.safetensors" -Subdir "vae"
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "vae/ltx-2.5-audio-vae-bf16.safetensors" -Subdir "vae"
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors" `
    -Subdir "latent_upscale_models"

# 4) 공식 Layout-to-Render IC-LoRA — 블렌더 클레이 영상 -> 실사
Get-Model -Repo "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render" `
    -File "ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors" -Subdir "loras"

# 5) 여러 인물/객체 고정용 MSR V2 (Apache 2.0)
Get-Model -Repo "LiconStudio/LTX-2.5-Multiple-Subject-Reference" `
    -File "LTX-2.5-Licon-MSR-V2.safetensors" -Subdir "loras"

Write-Host "P2 모델 다운로드 완료" -ForegroundColor Green
