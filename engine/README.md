# engine — P1 코어 파이프라인 (M-A 실사)

`docs/PRD.md` M2 / `docs/DESIGN.md` P1의 구현체. **M-A(실사)만** 다룬다.
M-B(2D 셀)·M-C(3D)·T0는 각각 P2.5 / P3.5 / P1.5에서 이 패키지 옆에 붙는다.

## 실행

```powershell
# 환경 점검 (ComfyUI·모델·ffmpeg·Ollama·디스크)
.\mokhwa.cmd env check

# 예상 시간만
.\mokhwa.cmd make --topic "비 오는 서울 골목" --seconds 15 --plan

# 15초(3씬) 1편
.\mokhwa.cmd make --topic "비 오는 서울 골목" --seconds 15

# 재개 (같은 run_id)
.\mokhwa.cmd make --run-id 20261116-133334

# 장면 1개만 다시
.\mokhwa.cmd make --run-id 20261116-133334 --scene 2 --force

# 목록
.\mokhwa.cmd status
```

`mokhwa.cmd`는 ComfyUI Portable의 임베디드 파이썬(`numpy`·`Pillow` 포함)을 쓴다.
다른 파이썬으로 실행하려면 `python cli.py ...`.

## 모듈

| 모듈 | 역할 | 핵심 규칙 |
|---|---|---|
| `config.py` | 경로·기본값 단일 출처 | D55 설치 경로 · D57 생성값 · D2 LLM |
| `errors.py` | `CineError` + 종료 코드 | 코드 접두사가 종료 코드 |
| `comfy.py` | ComfyUI HTTP | `/prompt` · `/history` · `/upload/image` · `/free` |
| `project.py` | run 디렉터리·state·재개 | `done(stage,key)` = 상태 AND 입력 해시 일치 |
| `script.py` | 대본 JSON (gemma4:12b) | 1회 교정 후 실패하면 중단(임의 생성 금지) |
| `keyframe.py` | SDXL 4시드 → 최고 선택 | 중앙 40% 라플라시안 분산 |
| `i2v.py` | Wan I2V → PNG 마스터 → CRF16 | `length=4k+1` · shift 8 · fp8 |
| `assemble.py` | 인코딩·크로스페이드·타임라인 | `sum(d) - crossfade×(n-1)` |

## 고정 규격 (바꾸지 말 것)

- **프레임 수**: `length = 4k+1`, 목표 이상으로 **올림**. 24fps 5초 = **121프레임(5.04초)**.
- **출력**: PNG 시퀀스 → `libx264 -crf 16 -pix_fmt yuv420p -movflags +faststart`.
  `SaveVideo`의 기본 압축은 통과 금지(D57).
- **클립 1개 = 씬 1개 = 5초**. 완성 길이는 씬 수로 환산(D50).
- **씬 프레임 정규화**: 생성된 프레임을 `work/<run>/frames/scene_XX/00001.png…`로
  하드링크해 인코딩한다. `ComfyUI/output/`에 이전 시도 프레임이 남아 있어도 섞이지 않는다.
- **VRAM 직렬화**: 키프레임(SDXL) → 클립(Wan) 사이에 `/free`를 호출한다.

## 캐시·재개

`work/<run_id>/state.json`에 단계별 `{status, key, started, finished, seconds}`를 남긴다.
`key`는 그 단계 입력의 sha1이다.

| 바꾼 것 | 다시 도는 단계 |
|---|---|
| 주제·길이·화풍·LLM | script → 이후 전부 |
| visual 프롬프트 | keyframes → clips → assemble |
| motion 프롬프트·스텝 | clips → assemble |
| 크로스페이드·CRF | assemble |

## 종료 코드

`0` 성공 · `3` 설정 · `4` 의존성(ffmpeg) · `5` 모델 · `6` ComfyUI ·
`7` LLM · `8` FFmpeg · `9` 산출물 · `10` 프로젝트 · `130` 중단

## 범위 밖 (아직)

- 오디오·TTS·자막(P2), 업스케일(FR-11), 립싱크(P5)
- M-B·M-C·T0
- UI — P3에서 이 CLI를 FastAPI 뒤에 둔다

## 검증 기록

| 날짜 | 조건 | 결과 |
|---|---|---|
| 2026-11-16 | 스모크 2씬 · 832×480 · 6스텝 | 10.08초 클립 2개 → 9.79초 완성(크로스페이드 0.3초), 6분 18초 |
| 2026-11-16 | 본 검증 3씬 · 1280×704 · 20스텝 | `final.mp4` + `timeline.json` |
