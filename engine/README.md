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
| `script.py` | 대본 JSON (gemma4:12b) | 1회 교정 후 실패하면 중단(임의 생성 금지) · `bible`/`shot`/`anchors` 검증 |
| `keyframe.py` | SDXL 4시드 → 최고 선택 | 중앙 40% 라플라시안 분산 · 앵커 프롬프트 · 컷 장면은 IPAdapter/img2img 참조 |
| `i2v.py` | Wan I2V → PNG 마스터 → CRF16 | `length=4k+1` · shift 8 · fp8 · 같은 `shot`은 마지막 프레임에서 연장 |
| `assemble.py` | 인코딩·크로스페이드·타임라인 | `sum(d) - crossfade×(n-1)` · `timeline`에 `shot` |

## 장면 간 일관성 (D63~D65)

두 축으로 나눈다. **연장은 픽셀, 컷은 앵커.**

| 축 | 트리거 | 수단 |
|---|---|---|
| 연장 | 앞 장면과 `shot`이 같다 | 앞 클립 **마지막 PNG**를 다음 클립 `start_image`로 넣는다 |
| 컷 | `shot`이 다르다 | **bible 앵커**(`char:`/`place:` + `look`)를 키프레임 프롬프트에 주입하고, 앞 장면 **키프레임을 참조 이미지로** 넣는다 |

`script.json`(`schema: 2`)이 이 정보를 담는다.

```json
{"schema": 2,
 "bible": {"characters": [{"id": "mina", "desc": "woman in a navy trench coat"}],
           "places":     [{"id": "alley", "desc": "narrow Seoul alley, wet asphalt"}],
           "look": "rainy blue hour, soft practical light"},
 "scenes": [{"id": 1, "shot": "S1", "anchors": ["char:mina", "place:alley"], "visual": "…"}]}
```

검증 규칙(어기면 1회 교정 요청 후 **중단**, 임의 보정 없음):

- `anchors`의 `char:`/`place:`는 반드시 `bible`에 존재
- 같은 `shot`의 장면은 **연속으로 붙어 있어야** 한다(떨어지면 체이닝이 엉뚱한 장면을 잇는다)
- 구버전 `script.json`(bible/shot 없음)은 각 씬이 자기 `shot`으로 읽혀 **체이닝 0**

### 체이닝 규격 (D65 실측)

| 항목 | 값 |
|---|---|
| 겹침 | **0프레임.** 앞 클립 마지막 프레임에서 그대로 시작 |
| 생성 길이 | 연장도 `4k+1` 그대로(5초 = 121프레임). 추가 생성 없음 |
| 이음새 기준 | `seam_mae` ≤ **3.0** (`verify.MAE_PASS`와 동일) |
| 대가 | 시작 프레임 1장이 앞 클립 마지막과 거의 같다(0.04초). 조립 크로스페이드가 덮는다 |
| 기록 | `state.json` clips 항목의 `overlap` · `seam_mae`, `timeline.json`의 `shot` |

겹침 8을 쓰지 않는 이유(832×480/6스텝 2클립 실측):

| 방식 | 이음새 MAE | 판정 |
|---|---|---|
| 겹침 0 · 시작 = 마지막 | **1.17** | ✅ 기준 3.0 이내 |
| 겹침 8 · 시작 = 마지막 | 39.89 | ❌ 트림한 8프레임만큼 시간이 건너뜀 |
| 겹침 8 · 시작 = 8프레임 앞 | 47.52 | ❌ 생성된 8프레임이 원본과 달라 정렬이 안 됨 |

모델은 시작 이미지를 거의 그대로 재현한다(MAE 1.17 / 1.30). 그래서 **시작점을 정확히
마지막 프레임에 두는 것**이 가장 중요한 변수이고, 겹침은 정렬 오차만 더한다.

### 컷 사이 참조 주입 (D64)

`shot`이 바뀌는 장면은 픽셀을 잇지 않는다. 대신 **그 인물이 나온 가장 가까운 앞
장면의 키프레임**을 SDXL 키프레임 생성에 참조로 넣는다.

| 항목 | 값 |
|---|---|
| 대상 | 컷 장면 중 `char:` 앵커가 있는 장면. 연장(같은 `shot`)은 체이닝이 대신하므로 참조 없음 |
| 참조 선택 | 앞 장면을 역순으로 훑어 `char:` 앵커가 겹치는 첫 장면의 키프레임(없으면 그 클립 첫 프레임) |
| 1순위 | `IPAdapterUnifiedLoader`(`PLUS (high strength)`) → `IPAdapterAdvanced` (weight 0.8, linear, V only) |
| 폴백 | 같은 시드에서 `LoadImage` → `ImageScale` → `VAEEncode` → `KSampler(denoise 0.55)` |
| 끄기 | `CINEMOKHWA_KF_REF=none` (또는 `img2img`로 고정) |
| 캐시 | 참조 **대상 장면 id** + 방식이 키프레임 캐시 키에 들어간다(같은 실행에서 앞 키프레임이 아직 없어도 키가 안정). 이번 실행에 포함되지 않은 대상만 파일 해시를 더한다 |

실측(832×480/8스텝, 같은 프롬프트·같은 시드):

| 확인 | 값 | 의미 |
|---|---|---|
| IPAdapter가 출력에 주는 영향 | w0.0 vs w1.0 **MAE 54.82** | 노드가 무시되지 않고 실제로 반영됨 |
| 폴백 | 프리셋을 일부러 깨뜨림 → `COMFY-002` → img2img로 성공 | 자동 폴백 동작 |
| 소요 | 키프레임 1장 5~20초(모델 로드 포함) · 4시드 × 3씬 **3분 41초**(참조 포함, 832×480/32스텝) | 4시드 × 3씬 ≈ 2~4분 |

인물 동일성은 수치로 판정하지 않는다. 픽셀 MAE는 구도가 달라지면 의미가 없고,
PRD §13.5와 같이 **육안 판정**이 우선이다. 파이프라인은 "참조가 실제로 쓰였는가"까지만 보증한다.

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
| `SYSTEM` 프롬프트·스키마 | script → 이후 전부 |
| bible·anchors | keyframes → clips → assemble |
| 참조 이미지(`char:` 앞 장면 내용)·`CINEMOKHWA_KF_REF` | keyframes → clips → assemble |
| `shot` 배치(어떤 씬이 연장인지) | clips → assemble |
| visual 프롬프트 | keyframes → clips → assemble |
| motion 프롬프트·스텝 | clips → assemble |
| 크로스페이드·CRF | assemble |

`state.json`의 `keyframes.items[]`에는 장면별 선택 시드·선명도·참조 방식·`elapsed`,
`clips.items[]`에는 프레임 수·재생 길이·`overlap`·`seam_mae`·`gen_seconds`·`elapsed`가 남는다.
run 단위 요약은 `docs/WORKLOG.md`에 1행으로 적는다(TASKS §0 규칙 8).

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
| 2026-11-16 | 스모크 2씬 · 832×480 · 6스텝 | 클립 2×121프레임 → 235프레임 9.79초 완성. 대본 48초 · 키프레임 2분 25초 · 클립 6분 18초 |
| 2026-11-16 | **본 검증 3씬 · 1280×704 · 20스텝** | `final.mp4` **349프레임 14.54초** 11.07MB 6.09Mbps · 클립 3×121프레임(각 5.04초, 18분 03초/개) · 대본 51초 · 키프레임 5분 21초 · 클립 54분 10초 · 조립 7초 · **벽시계 60.5분 ≤ 70분 예산** |
| 2026-11-16 | 본 검증 수치 보조(PRD §13.5) | YDIF 중앙값 1.04~6.99 **PASS** · 첫 프레임-키프레임 MAE ≤ 2.15 **PASS** · 장면 3의 중앙 선명도 0.61·YAVG σ 11.6은 **대본 의도(뒷모습·원경·보케)로 설명됨** — 육안 판정 대기 |
| 2026-11-17 | 일관성 통합 2씬 · 832×480 · 6스텝 (같은 `shot`) | 대본 schema 2 · 앵커 키프레임 · 클립 2×121프레임 · **연장 이음새 MAE 1.17** · `timeline` shot `S1/S1` · 총 9.783초 · exit 0 |
| 2026-11-17 | 이음새 방식 비교(같은 조건, 시도별 파일 분리 측정) | 시작 재현 MAE 1.17(A121)/1.30(A113) · 겹침 8은 39.89·47.52 → **겹침 0 확정(D65)** |
| 2026-11-17 | 대본 규칙 4(같은 shot = 구도 유지) 실 LLM 확인 | `gemma4:12b` 1회: 15초 3씬 → shot `S1/S1/S2`, 1→2는 "same medium shot · continues the slow zoom", 3은 wide로 컷. schema 2·bible·anchors 정상 |
| 2026-11-17 | 참조 대상 계산 시점 버그 | 3씬 통합 1차 실행에서 장면 3 참조가 `none`. 원인: 키프레임 생성 **전에** 참조 파일을 찾아 아직 없었음 → 대상은 대본으로 정하고 경로는 생성 시점에 찾도록 수정. 전체 실행 키는 대상 id 기반이라 생성 전후 동일(부분 재실행만 파일 해시 반영) |
| 2026-11-17 | 참조 통합 3씬 · 832×480 · 6스텝(`refpipe-01`, S1·S1·S2) — **기계 검증만 PASS** | 장면 1·2 `reference_mode=none`, 장면 3 **`ipadapter` · 참조 `keyframe02`** · 장면 2 연장 이음새 **MAE 1.17** · `timeline` `S1/S1/S2` · **349프레임 14.54초 6.97MB 3.83Mbps** · 단계 0.1/220.6/535.0/4.0초(합 12.7분) · 재실행 시 4단계 전부 건너뜀. **육안은 FAIL(아래 행)** |
| 2026-11-17 | **사용자 육안 판정 — 불합격** | ① 6스텝 영상 일렁·픽셀 이상·얼굴 다름 ② 키프레임 두 남자 다름 ③ 20스텝 본 검증도 뭉개짐·인물/배경 불일치. 측정: 연속프레임 MAE 6스텝 10.97~15.46 / 20스텝 1.50~7.26, 클립 끝 이탈 MAE 37~49. 참조 scene_02는 뒷모습 → 얼굴 정보 없음. **Q11/D66 결정 대기**, 숫자 PASS로 M2 통과 불가 |
| 2026-11-17 | `verify` 재실행 · 기준 오판 발견 | `refpipe-01` 종합 FAIL(장면 2) — 연장 장면의 첫 프레임(앞 클립 마지막)을 자기 키프레임과 비교해 MAE 40.19. P1-16에서 **컷/연장 임계 분리** 필요 |

### 수치 보조의 한계 (P1-08 설계 시 반영)

장면 3처럼 **피사체가 카메라에서 멀어지는 컷**은 중앙 40% 선명도가 구조적으로 떨어진다.
`visual`이 wide/behind/원경이면 선명도 비율은 **FAIL이 아니라 WARN**으로 두고,
같은 클립 내 최고 프레임 대비 상대값을 함께 본다. 판정은 항상 육안 체크리스트가 우선한다.

