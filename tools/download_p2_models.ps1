# P2 하이브리드 파이프라인용 모델 다운로드 (전부 무료 / 로컬)
#
# 쉬운 설명:
#   - LTX-2.5 영상 모델을 우리 컴퓨터(12GB 그래픽카드)에서 돌릴 수 있게
#     용량을 줄인 버전(GGUF)을 받습니다.
#   - 글자를 읽는 부품(텍스트 인코더)은 GGUF가 아직 없어서, ComfyUI가 직접
#     지원하는 4비트 버전(w4a8)을 받습니다.
#   - 블렌더 3D 구도를 실사로 바꿔주는 공식 부품과, 여러 인물을 각각 고정하는
#     부품도 함께 받습니다.
#
# 사용: powershell -File tools/download_p2_models.ps1
# 다시 실행해도 이미 받은 파일은 건너뜁니다(재다운로드 안 함).

$ErrorActionPreference = "Stop"

# hf 기본 전송(xet)이 대용량에서 정체되는 문제가 있어 일반 HTTPS로 받습니다.
$env:HF_HUB_DISABLE_XET = "1"

$HF = "C:\Users\mbc\AppData\Local\Python\pythoncore-3.12-64\Scripts\hf.exe"
$MODELS = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\models"
$STAGE = Join-Path $MODELS ".p2stage"

if (-not (Test-Path $STAGE)) { New-Item -ItemType Directory -Path $STAGE -Force | Out-Null }

# hf는 저장소 안의 폴더 구조를 그대로 만들어서 vae/vae처럼 겹치는 문제가 있습니다.
# 임시 폴더에 받은 뒤 원하는 위치로 옮겨서 경로를 항상 정확히 맞춥니다.
function Get-Model {
    param(
        [string]$Repo,
        [string]$File,
        [string]$Target,
        [switch]$Optional
    )
    $dest = Join-Path $MODELS $Target
    if (Test-Path $dest) {
        Write-Host "[건너뜀] $Target" -ForegroundColor DarkGray
        return
    }
    Write-Host "[$Repo] $File -> $Target" -ForegroundColor Cyan
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

    & $HF download $Repo $File --local-dir $STAGE --quiet
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) {
            Write-Host "[건너뜀] 승인 필요/없음 — $File (없어도 파이프라인은 동작)" -ForegroundColor Yellow
            return
        }
        throw "다운로드 실패: $Repo / $File"
    }

    $src = Join-Path $STAGE $File
    if (-not (Test-Path $src)) { throw "받은 파일을 못 찾음: $src" }
    Move-Item -LiteralPath $src -Destination $dest -Force
    Write-Host "[완료] $Target" -ForegroundColor Green
}

# 이전 실행에서 vae/vae 로 잘못 들어간 오디오 VAE를 바로잡습니다.
$misplaced = Join-Path $MODELS "vae\vae\ltx-2.5-audio-vae-bf16.safetensors"
if (Test-Path $misplaced) {
    Move-Item -LiteralPath $misplaced -Destination (Join-Path $MODELS "vae\ltx-2.5-audio-vae-bf16.safetensors") -Force
    $empty = Split-Path $misplaced -Parent
    if ((Get-ChildItem $empty -Force | Measure-Object).Count -eq 0) { Remove-Item $empty -Force }
    Write-Host "[정리] 오디오 VAE 경로 수정" -ForegroundColor Green
}

# 1) LTX-2.5 distilled DiT — GGUF UD-Q3_K_XL (약 11.2GB, 기본)
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "distilled/ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf" `
    -Target "unet\distilled\ltx-2.5-22b-distilled-UD-Q3_K_XL.gguf"

# 1-b) OOM 대비용 더 작은양자화 (약 8.9GB). 12GB 카드에서 메모리 부족 시 교체해 씀.
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "distilled/ltx-2.5-22b-distilled-UD-Q2_K_XL.gguf" `
    -Target "unet\distilled\ltx-2.5-22b-distilled-UD-Q2_K_XL.gguf"

# 2) Gemma4 12B 텍스트 인코더 — comfy-native w4a8 (약 9.9GB)
#    GGUF는 gemma4를 지원하지 않으므로 일반 safetensors / CLIPLoader 경로를 씁니다.
Get-Model -Repo "joeygambino/LTX-2.5-Quantized" `
    -File "gemma4-12b-ltx25-comfy-w4a8.safetensors" `
    -Target "text_encoders\gemma4-12b-ltx25-comfy-w4a8.safetensors"

# 3) 영상/오디오 VAE + 2배 업스케일러
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "vae/ltx-2.5-video-vae-conv-bf16.safetensors" `
    -Target "vae\ltx-2.5-video-vae-conv-bf16.safetensors"
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "vae/ltx-2.5-audio-vae-bf16.safetensors" `
    -Target "vae\ltx-2.5-audio-vae-bf16.safetensors"
Get-Model -Repo "unsloth/LTX-2.5-GGUF" `
    -File "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors" `
    -Target "latent_upscale_models\ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"

# 4) 공식 Layout-to-Render IC-LoRA — 선택 사항 (Hugging Face 승인 필요)
#    미승인 계정에서는 다운로드가 막힌다. 이 경우 3D 구도는 "프레임 앵커"로 주입하고
#    인물/소품 고정은 MSR V2로 처리하므로 파이프라인은 그대로 동작한다.
Get-Model -Repo "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render" `
    -File "ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors" `
    -Target "loras\ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors" `
    -Optional

# 5) 여러 인물/객체 고정용 MSR V2 (Apache 2.0)
Get-Model -Repo "LiconStudio/LTX-2.5-Multiple-Subject-Reference" `
    -File "LTX-2.5-Licon-MSR-V2.safetensors" `
    -Target "loras\LTX-2.5-Licon-MSR-V2.safetensors"

Write-Host "P2 모델 다운로드 완료" -ForegroundColor Green
