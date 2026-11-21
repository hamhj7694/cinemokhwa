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
| 지금 어디까지 | D66 ①·P1-16 커밋·푸시 완료. 서버 재시작으로 중단된 `identity-01` 재개 중. **3D 가이드 기획(D67~D69)**을 별도 브랜치에 구현·푸시 완료 |
| 이번 작업에서 한 일 | ① **D66 ① + P1-16 완료·커밋·푸시**(3개 functional unit) ② **사용자 3개 아이디어 모두 기록**(`docs/design/3D_GUIDED_REALISM.md`) — 1+2 채택, 3은 Q9로 보류 ③ **D67 3D 레이아웃 패스** 구현(결정론적 Scene3D, CPU 블록아웃 3씬 0.18초, Blender export) ④ **D68 이중 참조** 구현(IPAdapter 카드 + img2img 레이아웃 동시 주입, 6단계 파이프라인) ⑤ functional unit별 커밋·푸시 완료 |
| 숫자로 확인된 것 | 연장 이음새 **MAE 1.17~1.48**(기준 3.0 이하) · 카드 1장 **65.2초**, 832×480 3씬 키프레임 **246.0초** · 기존 run 재측정에서 드리프트 **34~48** 수치화 |
| **육안 판정(사용자, 2026-11-17)** | ❌ **FAIL** — ① 새 영상 일렁거림·픽셀 이상·얼굴 다름 ② 키프레임 두 남자 다름 ③ 본 검증 영상 뭉개짐·인물/배경 통일성 없음 (이후 개선분 재판정 필요) |
| 원인 후보(측정) | 6스텝은 연속프레임 MAE **10.97~15.46**(일렁임). 20스텝도 클립 끝이 시작 키프레임에서 **MAE 37~49** 이탈. 참조로 쓴 장면 2 키프레임은 **뒷모습**이라 얼굴 정보가 없음 |
| 다음 한 걸음 | `identity-01` 완료 → `mokhwa verify` → **사용자 육안 재판정**. 3D 가이드는 실 스모키(ComfyUI) 후 main 병합 — VRAM 직렬화 때문에 본 렌더 완료 후 실행 |

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

### 5-4. 육안 판정 결과 — 불합격 (2026-11-17)

사용자가 3개 산출물을 확인한 결과, **모두 육안 FAIL**이라고 보고했습니다.

| 대상 | 사용자 지적 | 측정으로 본 원인 |
|---|---|---|
| `refpipe-01/final.mp4` (6스텝) | 전체 일렁거림, 픽셀 이상, 얼굴 다름 | 연속프레임 MAE **10.97 / 15.46 / 7.66**. 20스텝 같은 조건은 7.26 / 1.50 / 4.80 → **6스텝은 스모크용이라 화질 기준 미달** |
| `refpipe-01/keyframes/` | 두 남자가 다름 | 장면 3 참조로 쓴 `scene_02.png`는 **"뒤어깨 샷"** 프롬프트로 생성돼 얼굴이 거의 안 보임 → 얼굴 고정에 쓸 정보가 없음 |
| `20261116-133334/final.mp4` (20스텝) | 픽셀 뭉개짐, 인물·배경 통일성 없음 | 클립 마지막 프레임이 시작 키프레임에서 **MAE 37.59 / 11.04 / 47.00** 이탈. I2V가 5초 동안 인물·배경을 점점 다른 그림으로 끌고 감 |

`mokhwa verify`는 `refpipe-01`에서 **종합 FAIL**, 본 검증에서 **WARN**을 냈습니다.
단, `refpipe-01` 장면 2의 FAIL은 **검증 기준 오판**입니다. 장면 2는 연장이라 첫 프레임이
앞 클립의 마지막 프레임인데, `verify`가 장면 2 자기 키프레임과 비교해 MAE 40.19를 냈습니다.
P1-16에서 **컷/연장 임계를 나눠야** 합니다.

> 결론: **숫자 PASS ≠ 화질 PASS**. 속도(60.5분)는 달성했지만 M2 게이트의 육안 기준은 미달입니다.
> **D66 ①은 사용자 승인(2026-11-17)을 받아 구현했습니다.** 개선 여부는 20스텝 본 검증의
> 육안 재판정으로만 확정합니다. ①로도 얼굴이 다르면 ③ FaceID/InstantID는 라이선스 확인 후
> 별도 승인을 받습니다.

---

## 6. 현재 상태

| 구분 | 내용 |
|---|---|
| 완료 | P0 환경 3/3 · P1 코어 · **P1-13/14/15/16** · **D66 ①·P1-16 커밋/푸시** · **D67 3D 레이아웃 + D68 이중 참조(브랜치, 커밋/푸시 완료)** · 작업 로그 체계 |
| 진행 | **`identity-01` 20스텝 렌더 재개 중**(scene 1 완료, scene 2부터 재생성) · 3D 가이드 실 스모키 대기 |
| 실패 | **P1-07 육안 FAIL** — 속도 PASS, 품질/일관성 미달 → `identity-01` + 3D 가이드로 재검증 |
| 차단 | **Q8** Figma Starter 호출 한도(P3 UI) · **Q9** M-B/M-C·정교 3D 모델 라이선스 확인 전 설치 금지 |
| 다음 결정 | `identity-01` 육안 PASS면 P1-07 마감. FAIL이면 D66 ③ 또는 3D 가이드 본 검증 |

전체 티켓 현황은 [`docs/TASKS.md`](TASKS.md), 최신 커밋은 `git log --oneline -5`.

---

## 7. 이번 작업 단위에서 바뀐 파일

| 파일 | 변경 |
|---|---|
| `engine/script.py` | `SCHEMA=2`, `bible`/`shot`/`anchors` 검증·교정, 앵커 인덱스, SYSTEM 규칙 4개 추가, 캐시 키에 스키마·SYSTEM 포함 |
| `engine/project.py` | `bible()` 조회 추가 |
| `engine/character.py` | **D66 ① 신규** — 정면 카드 4시드 생성, `references/char_<id>.png`, `bible.characters[].ref` 기록, 컷 참조 선택 |
| `engine/keyframe.py` | `prompt_for()`(앵커 문구), `reference_target()`/`reference_path()`(폴백 참조), `stage_key(ref_card=…)`, 워크플로 3분기(none/ipadapter/img2img), 자동 폴백 |
| `engine/layout3d.py` | **D67 신규** — 결정론적 `Scene3D`, numpy+PIL 블록아웃, `layouts/layout_NN.png`, `export_blender()` |
| `engine/verify.py` | **P1-16** — `shot`으로 컷/연장 구분, 연장=앞 클립 끝 이음새, 컷=SSIM·팔레트, 드리프트 WARN |
| `tests/test_layout3d.py` | D67/D68 오프라인 검증 — 결정성·투사·캐시·이중참조 노드 연결 ALL PASS |
| `docs/design/3D_GUIDED_REALISM.md` | 사용자 3아이디어 기록 + D67~D69 채택/보류 근거 |
| `engine/i2v.py` | `CHAIN_OVERLAP=0`, `last_frame()`, `_mae()`, `generate(chain_from=…)`, 메타에 `overlap`/`seam_mae`/**`gen_seconds`·`elapsed`** |
| `engine/assemble.py` | `timeline.json`에 `shot` 추가 |
| `engine/config.py` | `kf_reference`·`ipadapter_preset`·`ipadapter_weight`·`img2img_denoise` |
| `cli.py` | `chain_sources()`, **5단계 파이프라인(카드 단계 추가)**, 카드→키프레임 참조 배선, 클립 체이닝, `cmd_batch` 복원 |
| `docs/DESIGN.md` | D63~D66 + **D67(3D 패스) · D68(기존 실사 자산) · D69(정교 3D 보류)** |
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
| **5단계** 소요(대본·**캐릭터 카드**·키프레임·클립·조립), 장면별 시간, 이음새 MAE | `C:\Users\mbc\mokhwa\work\<run_id>\state.json` | 자동 |
| 단계 완료 시각 | 같은 폴더의 `run.log` | 자동 |
| ComfyUI 서버 로그 | `C:\Users\mbc\mokhwa\logs\comfyui.out.log` / `.err.log` | 자동 |
| run 요약(조건·결과·소요) | [`docs/WORKLOG.md`](WORKLOG.md) | 티켓 종료 시 수동 1행 |
| 모델 성능 기준값 | [`docs/ENVIRONMENT.md`](ENVIRONMENT.md) §5 | 측정 시 수동 |

---

## 9. 다음 단계

1. ~~D66 결정~~ / ~~P1-16 검증 수정~~ / ~~D67~D69 기획·코드~~ — 완료.
2. `identity-01` 렌더 완료 → `mokhwa verify --run-id identity-01` → `final.mp4` **사용자 육안 재판정**.
3. 3D 가이드 실 스모키(저해상도, ComfyUI) → 결과 확인 후 `feature/3d-guided-realism`을 main에 병합.
4. 육안 PASS면 P1-07/P1-15/P1-17 마감. FAIL이면 D66 ③ 또는 3D 가이드 본 검증.
5. P1-09(재시도)·P1-10(manifest)·P1-11(batch)·P1-12(화풍)는 그 뒤.
6. M-B/P2.5·M-C/P3.5·정교 3D 모델은 **Q9 해제 전 설치 금지**.

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

| # | 항목 | 상태 / 필요한 사람 |
|---|---|---|
| 1 | P1-07 육안 PASS/FAIL (§13.5 8항목) | ❌ **FAIL 보고됨**(2026-11-17) → `identity-01` 재검증 결과 대기 |
| 2 | 컷 사이 인물 동일성 | ❌ **FAIL 보고됨** → D66 ① 적용본 육안 재판정 대기 |
| 3 | ~~D66 인물 동일성 전략~~ | ✅ **① 승인·구현 완료**. 실패 시 ③ FaceID/InstantID는 라이선스 확인 후 별도 승인 |
| 4 | Q8 Figma 한도 리셋/플랜 | 사용자 |
| 5 | Q9 M-B·M-C·정교 3D 모델 라이선스 근거 | 사용자/조사 |
| 6 | 3D 가이드 실 스모키 후 main 병합 여부 | 나(자동) → 최종 확인은 사용자 |
