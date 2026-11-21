# P2 하이브리드 파이프라인용 ComfyUI 커스텀 노드 설치
#
# 쉬운 설명:
#   - 용량 줄인 영상 모델(LTX-2.5)과 사진 모델(Krea 2)을 읽는 노드(GGUF 포크)
#   - LTX-2.5 영상 생성 노드와 공식 워크플로(LTXVideo)
#   - 여러 인물을 각각 고정하는 노드(MSR)
#   - 화면에 핀을 꽂아 위치를 고정하는 노드(FL-Path)
#   를 ComfyUI에 설치합니다. 이미 있으면 건너뜁니다.
#
# 주의: Krea 2 GGUF는 일반 ComfyUI-GGUF가 아키텍처를 몰라서 포크가 필요합니다.
#       포크는 city96 코드에 krea2만 추가한 버전이라 LTX GGUF도 그대로 읽습니다.

$ErrorActionPreference = "Stop"
$NODES = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\custom_nodes"
$PY = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\python_embeded\python.exe"
$BACKUP = "C:\Users\mbc\mokhwa\tools\backup"

$repos = @(
    @{ Name = "ComfyUI-GGUF";        Url = "https://github.com/RealRebelAI/ComfyUI-GGUF_KREA-2.git"; NeedKrea2 = $true },
    @{ Name = "ComfyUI-LTXVideo";    Url = "https://github.com/Lightricks/ComfyUI-LTXVideo.git";       NeedKrea2 = $false },
    @{ Name = "ComfyUI-LTX2.5-MSR";  Url = "https://github.com/liconstudio/ComfyUI-LTX2.5-MSR.git";    NeedKrea2 = $false },
    @{ Name = "ComfyUI_FL-Path-Animator"; Url = "https://github.com/filliptm/ComfyUI_FL-Path-Animator.git"; NeedKrea2 = $false }
)

foreach ($r in $repos) {
    $dest = Join-Path $NODES $r.Name
    if (Test-Path $dest) {
        $loader = Join-Path $dest "loader.py"
        if ($r.NeedKrea2 -and (Test-Path $loader)) {
            $src = Get-Content $loader -Raw
            if ($src -notmatch 'krea2') {
                Write-Host "[교체] ComfyUI-GGUF -> Krea2 지원 포크" -ForegroundColor Yellow
                if (-not (Test-Path $BACKUP)) { New-Item -ItemType Directory -Path $BACKUP -Force | Out-Null }
                Move-Item -LiteralPath $dest -Destination (Join-Path $BACKUP "ComfyUI-GGUF-city96") -Force
            } else {
                Write-Host "[건너뜀] $($r.Name) (Krea2 포크 이미 설치됨)" -ForegroundColor DarkGray
                continue
            }
        } else {
            Write-Host "[건너뜀] $($r.Name) (이미 설치됨)" -ForegroundColor DarkGray
            continue
        }
    }
    Write-Host "[설치] $($r.Name)" -ForegroundColor Cyan
    git clone --depth 1 $r.Url $dest
    if ($LASTEXITCODE -ne 0) { throw "클론 실패: $($r.Name)" }
    $req = Join-Path $dest "requirements.txt"
    if (Test-Path $req) {
        & $PY -m pip install -r $req
        if ($LASTEXITCODE -ne 0) { throw "의존성 설치 실패: $($r.Name)" }
    }
}

Write-Host "커스텀 노드 설치 완료. ComfyUI를 재시작하세요." -ForegroundColor Green
