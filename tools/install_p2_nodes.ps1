# P2 하이브리드 파이프라인용 ComfyUI 커스텀 노드 설치
#
# 쉬운 설명:
#   - 용량 줄인 LTX-2.5 모델을 읽을 수 있는 노드(GGUF)
#   - LTX-2.5 영상 생성 노드와 공식 워크플로(LTXVideo)
#   - 여러 인물/사물을 각각 고정하는 노드(MSR)
#   - 화면에 핀을 꽂아 위치를 고정하는 노드(FL-Path)
#   를 ComfyUI에 설치합니다. 이미 있으면 건너뜁니다.

$ErrorActionPreference = "Stop"
$NODES = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\custom_nodes"
$PY = "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\python_embeded\python.exe"

$repos = @(
    @{ Name = "ComfyUI-GGUF";        Url = "https://github.com/city96/ComfyUI-GGUF.git" },
    @{ Name = "ComfyUI-LTXVideo";    Url = "https://github.com/Lightricks/ComfyUI-LTXVideo.git" },
    @{ Name = "ComfyUI-LTX2.5-MSR";  Url = "https://github.com/liconstudio/ComfyUI-LTX2.5-MSR.git" },
    @{ Name = "ComfyUI_FL-Path-Animator"; Url = "https://github.com/filliptm/ComfyUI_FL-Path-Animator.git" }
)

foreach ($r in $repos) {
    $dest = Join-Path $NODES $r.Name
    if (Test-Path $dest) {
        Write-Host "[건너뜀] $($r.Name) (이미 설치됨)" -ForegroundColor DarkGray
        continue
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
