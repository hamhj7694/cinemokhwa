# HANDOFF — 씨네목화 인수인계

> 최종 갱신: 2026-11-17 · P1-15(장면 간 일관성) 작업 단위 종료 시점
> 읽는 사람: 이 프로젝트를 처음 보는 사람(개발자·비개발자 모두)
> 더 깊은 내용: `docs/DESIGN.md`(결정 로그) · `docs/TASKS.md`(티켓) · `docs/WORKLOG.md`(run별 실측) · `engine/README.md`(구현 규격)

---

## 1. 한 문단 요약

씨네목화는 **"글 한 줄을 넣으면 로컬 PC에서 영상이 나오는"** 무료 영상 제작 도구다.
외부 유료 API 없이 RTX 3060 12GB 한 대에서 대본 → 장면 그림(키프레임) → 5초 영상 클립 → 이어 붙인 `final.mp4`까지 만든다.
지금은 **P1(실사 모드 M-A)의 마무리 단계**이며, 이번 작업에서는 **여러 장면이 이어질 때 같은 인물·같은 장소처럼 보이게 하는 기능**을 넣었다.
핵심 아이디어는 두 가지다. **이어지는 장면은 앞 영상의 마지막 그림을 그대로 시작점으로 쓰고(연장), 장면이 바뀌는 컷은 앞 장면의 그림을 참고 자료로 넣는다(참조).**

---

## 2. 5분 요약

| 질문 | 답 |
|---|---|
| 무엇을 만드나 | 텍스트/목소리 → 영상 1편을 **완전 로컬·무료·무제한**으로 만드는 파이프라인 |
| 지금 어디까지 | P1 코어 완료. 15초 1편이 **60.5분**(예산 70분)에 나오는 것 확인. 일관성 기능(P1-13~15) 구현·검증 중 |
| 이번 작업에서 한 일 | ① 대본에 `bible`(인물·장소 사전) + `shot`(연속 촬영 단위) 추가 ② 같은 `shot`은 앞 클립 마지막 프레임에서 연장 ③ 컷은 IPAdapter로 앞 키프레임 참조 주입, 실패 시 img2img 폴백 |
| 숫자로 확인된 것 | 연장 이음새 **MAE 1.17**(기준 3.0 이하) · IPAdapter가 출력에 실제 반영(MAE 54.82) · 폴백 자동 전환 성공 · 3씬 통합: 장면 3만 참조, 349프레임 14.54초, 12.7분 |
| 아직 못 한 것 | 컷 사이 **인물 동일성 육안 판정**(수치로 판정 불가) · 15초 본 검증(P1-17) · P1-07 육안 판정 |
| 다음 한 걸음 | P1-16(검증 확장) → P1-17(15초 본 검증 ≤70분) |

---

## 3. 저장소와 실행 폴더는 다르다

| 구분 | 경로 | 내용 |
|---|---|---|
| 코드 저장소 | `C:\Users\mbc\Documents\git\cinemokhwa` | 소스·문서. GitHub `hamhj7694/cinemokhwa` |
| 실행/데이터 | `C:\Users\mbc\mokhwa` | ComfyUI·모델·`work/<run_id>/` 결과물 |

- 코드는 git으로 관리하고, **모델 가중치와 생성물은 git에 넣지 않는다**(용량).
- CLI 진입점은 저장소 루트의 `mokhwa.cmd`. 내부적으로 ComfyUI 임베디드 파이썬을 쓴다.

---

## 4. 파이프라인 한눈에

| # | 단계 | 하는 일 | 결과물 |
|---|---|---|---|
| 1 | 대본 | `gemma4:12b`(Ollama)가 주제 → 장면 JSON | `script.json` |
| 2 | 키프레임 | SDXL 4시드 생성 → 중앙 선명도 최고 1장 | `keyframes/scene_XX.png` |
| 3 | 클립 | Wan 2.2 I2V, 5초(121프레임) | `clips/scene_XX.mp4` |
| 4 | 조립 | FFmpeg 크로스페이드 | `final.mp4` + `timeline.json` |
| + | 검증 | 선명도·깜빡임·밝기 변화 측정 | `metrics.json` |

```powershell
cd C:\Users\mbc\Documents\git\cinemokhwa
.\mokhwa.cmd env check                         # 환경 점검(종료 코드 0이면 정상)
.\mokhwa.cmd make --topic "비 오는 서울 골목" --seconds 15
.\mokhwa.cmd verify --run-id <run_id>
.\mokhwa.cmd status
```

---

## 5. 이번 작업의 핵심: 장면 간 일관성

### 5-1. 비유

영화를 찍을 때 **같은 촬영(같은 `shot`)** 안에서 카메라가 계속 돌면 앞 화면과 이어져야 한다.
반대로 **다른 촬영(컷)** 으로 넘어가면 화면은 끊기지만, **같은 사람·같은 장소**로 보여야 한다.
그래서 해결책을 두 축으로 나눴다.

| 축 | 언제 | 방법 | 왜 |
|---|---|---|---|
| **연장** | 앞 장면과 `shot`이 같을 때 | 앞 클립의 **마지막 PNG**를 다음 클립의 시작 이미지로 그대로 넣는다 | 픽셀이 곧 정답. 새로 그리면 얼굴·옷이 바뀐다 |
| **컷** | `shot`이 바뀔 때 | 앞 장면 **키프레임을 참조 이미지**로 SDXL에 주입(IPAdapter) + `bible` 앵커 문구 상시 주입 | 구도는 달라도 인물·장소의 생김새를 유지 |

### 5-2. 대본에 추가된 약속(`schema: 2`)

```json
{
  "schema": 2,
  "bible": {
    "characters": [{"id": "jun", "desc": "man in a grey coat, short black hair"}],
    "places": [{"id": "alley", "desc": "narrow wet Seoul alley at night"}],
    "look": "rainy night, soft neon reflections"
  },
  "scenes": [
    {"id": 1, "shot": "S1", "anchors": ["char:jun", "place:alley"], "visual": "wide shot, …"},
    {"id": 2, "shot": "S1", "anchors": ["char:jun", "place:alley"], "visual": "same man keeps walking, …"},
    {"id": 3, "shot": "S2", "anchors": ["char:jun"], "visual": "medium close up of the same man …"}
  ]
}
```

- `bible` = 인물·장소 사전. 여기의 문구가 모든 키프레임 프롬프트에 자동으로 붙는다.
- `shot` = 연속 촬영 단위. **같은 값이 연속으로 오면 연장**, 값이 바뀌면 **컷**.
- `anchors` = 이 장면에 누가/어디가 나오는지 표시. `char:`가 겹치는 앞 장면을 찾아 참조 이미지로 쓴다.
- 검증: `anchors`가 `bible`에 없거나, 같은 `shot`이 떨어져 있으면 **1회 교정 요청 후 중단**(임의 보정 금지).

### 5-3. 실측으로 확정한 규격

| 항목 | 확정값 | 근거 |
|---|---|---|
| 연장 겹침 | **0프레임** | 겹침 8은 이음새 MAE 39.89/47.52로 실패, 겹침 0은 **1.17** |
| 클립 길이 | 5초 = **121프레임**(`4k+1` 유지) | Wan 제약 |
| 참조 1순위 | `IPAdapterUnifiedLoader` "PLUS (high strength)" + `IPAdapterAdvanced`(weight 0.8, linear) | 영향력 MAE 54.82로 실제 반영 확인 |
| 참조 폴백 | `LoadImage → ImageScale → VAEEncode → KSampler(denoise 0.55)` | IPAdapter 프리셋 고장 주입 → `COMFY-002` → 자동 전환 성공 |
| 참조 끄기 | `CINEMOKHWA_KF_REF=none` | 문제 분리용 스위치 |
| 캐시 | 참조 **대상 장면 id** + 방식이 키프레임 캐시 키에 포함(새 run과 재실행의 키가 같다). 이번 실행에 없는 대상만 파일 해시 추가 | 참조 대상을 바꾸거나 앞 장면 내용이 바뀌면 키프레임부터 다시 생성 |

> **왜 수치로 인물 동일성을 판정하지 않나**: 구도가 달라지면 픽셀 비교(MAE)는 의미가 없다.
> 기계는 "참조가 실제로 쓰였는가"까지만 보증하고, "같은 사람으로 보이는가"는 PRD §13.5 **육안 체크리스트**로 판정한다.

---

## 6. 현재 상태

| 구분 | 내용 |
|---|---|
| 완료 | P0 환경 3/3 · P1 코어(P1-01~06, 08) · **P1-13 대본 연속성** · **P1-14 클립 체이닝** · **P1-15 참조 주입**(3씬 통합 PASS) |
| 진행 | P1-07 육안 판정 대기 |
| 다음 | P1-16 `verify` 확장(경계·팔레트·SSIM) → P1-17 15초 본 검증(≤70분) |
| 차단 | **Q8** Figma Starter 호출 한도(P3 UI) · **Q9** M-B/M-C 모델 라이선스 확인 전 설치 금지 |
| 사용자 결정 대기 | P1-07 `final.mp4`를 `docs/PRD.md` §13.5 8항목으로 육안 PASS/FAIL |

전체 티켓 현황은 [`docs/TASKS.md`](TASKS.md), 최신 커밋은 `git log --oneline -5`.

---

## 7. 이번 작업 단위에서 바뀐 파일

| 파일 | 변경 |
|---|---|
| `engine/script.py` | `SCHEMA=2`, `bible`/`shot`/`anchors` 검증·교정, 앵커 인덱스, SYSTEM 규칙 4개 추가, 캐시 키에 스키마·SYSTEM 포함 |
| `engine/project.py` | `bible()` 조회 추가 |
| `engine/keyframe.py` | `prompt_for()`(앵커 문구), `reference_target()`/`reference_path()`(참조 선택), 워크플로 3분기(none/ipadapter/img2img), 자동 폴백, 캐시 키·메타에 참조 기록 |
| `engine/i2v.py` | `CHAIN_OVERLAP=0`, `last_frame()`, `_mae()`, `generate(chain_from=…)`, 메타에 `overlap`/`seam_mae`/**`gen_seconds`·`elapsed`** |
| `engine/assemble.py` | `timeline.json`에 `shot` 추가 |
| `engine/config.py` | `kf_reference`·`ipadapter_preset`·`ipadapter_weight`·`img2img_denoise` |
| `cli.py` | `chain_sources()`(연장·참조 대상 계산), 키프레임 참조 배선, 클립 체이닝, 사라졌던 `cmd_batch` 복원 |
| `docs/DESIGN.md` | D63(2축) · D64(참조 주입) · D65(겹침 0) |
| `docs/TASKS.md` | P1-13/14/15 상태, P1-16/17 추가 |
| `engine/README.md` | 일관성 규격·실측표·참조 절차 |
| `docs/WORKLOG.md` | run별 실측 로그(신규) — 기록 규칙·과거 run 역기입 |
| `docs/HANDOFF.md` | 이 문서(신규) |

---

## 8. 검증하는 방법

| 검증 | 명령/방법 | 기대 |
|---|---|---|
| 환경 | `.\mokhwa.cmd env check` | 종료 코드 0 |
| 문법 | `& $py -m py_compile cli.py engine\*.py` | 오류 0 |
| 오프라인 단위 테스트 | `C:\Users\mbc\AppData\Local\Temp\opencode\` 의 테스트 스크립트 | ALL PASS |
| 3씬 통합 | `.\mokhwa.cmd make --run-id refpipe-01` | 장면 1·2 `reference_mode=none`, 장면 3 `ipadapter` |
| 이음새 | `state.json` clips의 `seam_mae` | ≤ 3.0 |
| 수치 품질 | `.\mokhwa.cmd verify --run-id <id>` | §13.5 3종 출력 |
| 최종 판정 | `final.mp4` 육안 | §13.5 8항목 평균 ≥ 3.5 |

### 8-1. 작업 기록이 남는 곳

| 기록 | 위치 | 자동 여부 |
|---|---|---|
| 단계별 소요, 장면별 키프레임/클립 시간, 이음새 MAE | `C:\Users\mbc\mokhwa\work\<run_id>\state.json` | 자동 |
| 단계 완료 시각 | 같은 폴더의 `run.log` | 자동 |
| ComfyUI 서버 로그 | `C:\Users\mbc\mokhwa\logs\comfyui.out.log` / `.err.log` | 자동 |
| run 요약(조건·결과·소요) | [`docs/WORKLOG.md`](WORKLOG.md) | 티켓 종료 시 수동 1행 |
| 모델 성능 기준값 | [`docs/ENVIRONMENT.md`](ENVIRONMENT.md) §5 | 측정 시 수동 |

---

## 9. 다음 단계

1. ~~P1-15 마감~~ — **완료**(`refpipe-01`): 장면 3만 `ipadapter(keyframe02)`, 연장 2장면 `none`, 이음새 MAE 1.17, 349프레임 14.54초, 재실행 시 전 단계 건너뜀.
2. **P1-16** — `mokhwa verify` 확장: 컷 경계(장면 전환)와 연장 경계를 다른 임계로, 팔레트·SSIM 지표 추가.
3. **P1-17** — 일관성 포함 **15초 3씬/1280×704/20스텝** 본 검증. 목표 **≤ 70분**, §13.5 수치 PASS, 육안 판정.
4. P1-09(재시도)·P1-10(manifest)·P1-11(batch)·P1-12(화풍)는 그 뒤.
5. M-B/P2.5·M-C/P3.5는 **Q9 해제 전 모델 설치 금지**.

---

## 10. 함정 — 반복하지 말 것

| 함정 | 대응 |
|---|---|
| ComfyUI 출력 폴더에 이전 시도 프레임이 쌓임 | `frames/scene_XX/`로 정규화 후 인코딩. **같은 prefix 재생성 시 번호가 이어 붙는다**(측정 시 시도별 번호 범위 분리) |
| 컷 참조를 "앞 키프레임 파일이 있는지"로 판단 | 3씬 통합에서 파일이 아직 없어 참조가 `none`이 됐다. **대상은 대본(`anchors`)으로 정하고, 경로는 생성 직전에 찾는다** |
| 겹침 프레임으로 이음새를 맞추려는 시도 | 실측 실패(MAE 39.89). **겹침 0**이 정답(D65) |
| `LoadImage`가 임의 경로를 못 읽음 | ComfyUI `input/`만 읽는다 → `/upload/image` 사용 |
| Wan이 한글·영상 내 텍스트를 못 그림 | 자막은 FFmpeg 번인으로 해결 |
| 전역 선명도로 품질 판정 | 보케·원경을 오판 → 중앙 40% 측정, wide/behind는 WARN |
| `SYSTEM` 프롬프트를 바꾸면 기존 run이 대본부터 재실행 | 의도된 동작(캐시 키에 포함) |
| 콘솔 한글 깨짐 | `$env:PYTHONIOENCODING="utf-8"`, 스크립트는 ASCII, 커밋 메시지는 `-F 파일` |
| ComfyUI가 예고 없이 종료 | 로그 `C:\Users\mbc\mokhwa\logs\comfyui.out.log`. 재기동 후 같은 `--run-id`로 재개 |

---

## 11. 최소 용어 사전

| 용어 | 뜻 |
|---|---|
| 키프레임 | 영상 클립의 **첫 그림**. I2V 모델이 이 그림에서 움직임을 만든다 |
| I2V | Image-to-Video. 그림 1장 → 5초 영상 |
| 체이닝 | 앞 클립의 마지막 프레임을 다음 클립의 시작으로 쓰는 연장 방식 |
| 컷 | 촬영 단위(`shot`)가 바뀌는 장면 전환 |
| IPAdapter | 참조 이미지의 인물·분위기를 생성에 반영하는 ComfyUI 노드 |
| img2img | 참조 이미지를 노이즈로 살짝 덮은 뒤 다시 그리는 폴백 방식(denoise 0.55) |
| MAE | 두 이미지의 평균 픽셀 차이. 낮을수록 같다 |
| `bible` | 대본의 인물·장소·조명 사전. 프롬프트 일관성의 기준 |
| run_id | 한 편의 작업 폴더 이름. 재개·부분 재생성의 단위 |

---

## 12. 결정이 필요한 것

| # | 항목 | 필요한 사람 |
|---|---|---|
| 1 | P1-07 `final.mp4` 육안 PASS/FAIL (§13.5 8항목) | 사용자 |
| 2 | 컷 사이 인물 동일성 육안 판정(3씬 통합 결과) | 사용자 |
| 3 | Q8 Figma 한도 리셋/플랜 | 사용자 |
| 4 | Q9 M-B·M-C 모델 라이선스 근거 | 사용자/조사 |
