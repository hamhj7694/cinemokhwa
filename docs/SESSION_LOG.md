# 세션 작업 로그 & 중요 사항

> 최종 갱신: 2026-11-21 (진행 중 — 계속 갱신)
> 용도: 새 세션/사용자 사후 확인용. 기능 단위 커밋·푸시, 판단 근거, 미해결 사항을 모두 여기에 남긴다.
> 최종 요약은 항상 [`FINAL_REPORT.md`](FINAL_REPORT.md)를 최신화한다.

---

## 2026-11-21 세션

### 배경
- 2026-11-17 세션에서 D66 ①(정면 캐릭터 카드) + P1-16(검증 기준 수정) 구현, 문서 갱신까지 완료.
- `identity-01` 본 검증(1280×704/20스텝/3씬) 진행 중 서버가 재시작돼 백그라운드 명령 2개 취소.
- 사용자 지시: (1) 진행분 빠르게 커밋·푸시 (2) 기획 중간 점검 후 내가 방향 결정해 자동 완성 (3) 질문 금지
  (4) 기능 단위 커밋·푸시 (5) 새 작업은 브랜치 (6) 작업 로그/최종 보고서 상시 최신화.

### 완료한 일 (순서)

| # | 기능 단위 | 내용 | 커밋 | 브랜치 | 푸시 |
|---|---|---|---|---|---|
| 1 | D66 ① 엔진 | `character.py` 신규, `project.py` 5단계, `keyframe.py ref_card`, 문서 동기화 | `2b37b5b` | main | ✅ |
| 2 | P1-16 검증 + CLI | `verify.py` 재작성, `cli.py` 5단계·verify 표 | `b962326` | main | ✅ |
| 3 | Figma 재개 문서 | 기존 미추적 2파일 추가 | `36677de` | main | ✅ |
| 4 | D67~D69 기획 + 3D 레이아웃 엔진 | `3D_GUIDED_REALISM.md`, `layout3d.py`, `tests/test_layout3d.py`, DESIGN D67~D69 | `7f0e45f` | feature/3d-guided-realism | ✅ |
| 5 | D68 이중 참조 + 6단계 | `keyframe.py` IPAdapter+img2img 동시, `project.py` 6단계, `cli.py` 배선, 테스트 | `dcf4a46` | feature/3d-guided-realism | ✅ |
| 6 | 조명·연장 수정 + D70 Blender | `prompt_for()` 조명 고정(`5d61132`) → 연장 씬 레이아웃 미주입(`30efa2a`) → Blender 4.5.16 설치·`render_blender()` 연결(`5a3c151`) | `5a3c151` | main | ✅ |
| 7 | 육안 비교표 생성기 | `tools/contact_sheet.py` — run별 대표 프레임 4셀 그리드 PNG | `13399a3` | main | ✅ |
| 8 | D71 씬 간 밝기 검증 | `verify.py` CROSS_YAVG_WARN=25/FAIL=50, `keyframe.py` 밝기 기준 선택, 회귀 테스트 | `5e6889d` | main | ✅ |
| 9 | D71b 절대 선명도 하한 | 상대 60% → `MIN_CENTER_SHARPNESS=40`,guided-50 재시작 | `7f2de01` | main | ✅ |
| 10 | D71b 조기 경고 + D72 | `cli.py` 밝기 조기 경고(`c3b2161`), verify motion-aware step/std 판정, guided-50 검증 완료 | (이번 커밋) | main | ✅ |

main 푸시 범위: `482f99e..36677de`. feature 브랜치는 `origin/feature/3d-guided-realism` 추적 중.

### 진행 중

| 항목 | 상태 | 다음 |
|---|---|---|
| 최종 육안 판정 | **사용자 차례** — 자동 검증은 FAIL 해소(WARN). 비교표 `C:\Users\mbc\mokhwa\work\contact_compare.png` | `guided-50/final.mp4`를 ①~④와 비교해 귀속 확인 |
| (선택) scene 2 드리프트 WARN | 연장 씬 카메라 이동에 따른 자연 변화로 판단, WARN 유지 | 육안으로 이질감 있으면 scene 2만 `--force` 재생성 |

### 중요 판단 근거

| 결정 | 근거 |
|---|---|
| D66 ① 채택 | 뒷모습 키프레임 참조가 얼굴 불일치의 직접 원인 → 정면 카드로 얼굴 정보 항상 포함 |
| P1-16 연장 기준 | 같은 shot은 시작점이 앞 클립 마지막 프레임 → 자기 키프레임 비교는 오판(MAE 40.19) |
| 커밋 분리 | `cli.py`가 두 기능에 걸려 카드 엔진 → `cli.py`+`verify.py` 순으로 분리해 기능 단위 유지 |
| 신규 작업 브랜치 | 기존 main 커밋 보존 요청에 따라 3D 기획은 `feature/3d-guided-realism`에서 진행 |
| Blender 미설치 → 소프트웨어 렌더 (D67 초기) | 당시 설치 없이 즉시 동작해야 했고 목적은 "예쁜 3D"가 아닌 **구도 고정**이었음. 이후 D70에서 실제 Blender 설치·기본 백엔드화 |
| Blender 채택 (D70) | Unity는 실시간 게임 엔진이라 정적 구도 도면에 과함. Blender는 무료 GPL·오프라인 렌더·Python 자동화. 사용자가 "가능하면 Blender 쓰면 좋겠다"고 명시 |
| 아이디어 3 보류 (D69/Q9 종결) | Hunyuan3D 2.1은 한국이 라이선스 지역에서 제외, TRELLIS.2는 MIT지만 의존성 비상업용+24GB VRAM → 부적합 판정. Blender 도면 방식 유지 |
| D71 씬 간 밝기 검사 | 개별 클립 PASS여도 Yavg 34/35/116(차이 81.97)이면 "다른 공간"처럼 보임. 컷 내 std만으로는 못 잡으므로 run 전체 max-min 검사 추가 |
| D71b 절대 선명도 하한 | 어두운 그림이 라플라시안 분산이 인위적으로 커서 "선명도 최고"가 암부를 선택(Y112/lap52가 Y35/lap174에 밀림). 상대 60%도 부족해 절대 하한 40 적용 |
| D72 motion-aware 밝기 판정 | guided-50 scene2는 std 5.46이지만 step/std 0.35의 단일 아치(103→125→109) = 자연 조명 통과. 깜빡임은 step/std가 커서 계속 FAIL. WARN은 육안 게이트용으로 유지 |

### 미해결 / 주의

- Q9 조사 완료·종결 — Hunyuan3D(한국 제외)/TRELLIS.2(의존성 제약) 모두 부적합. 정교 3D 모델 설치 안 함.
- `guided-40`은 씬 간 밝기 차이 81.97로 FAIL, `guided-50`은 D71b+D72 적용으로 **WARN(FAIL 없음)** 완료. auto 검증 종료.
- D72: scene 2 std 5.46이지만 step/std 0.35 완만 아치 → PASS. 고주파 깜빡임은 계속 FAIL. 숫자 PASS만으로 통과 불가 원칙 유지.
- 사용자 지시: 중간 확인 없이 멈추지 말고 계속 진행. 설치 필요 시 묻지 말고 바로 설치.
- 이 모델은 이미지 입력을 못 읽음 → 카드/키프레임/영상 육안 판정은 사용자만 가능.
- ComfyUI 출력에 이전 시도 프레임 누적 주의. 재개 전 `identity-01`의 scene 02 잔여 프레임은 0개로 확인됨.
- `test_layout3d.py`의 `Config()` 사용은 모델 로드를 하지 않는 순수 워크플로 검증임.

---

## 커밋 기록

| 해시 | 브랜치 | 메시지 요지 |
|---|---|---|
| `2b37b5b` | main | 인물별 정면 기준 이미지로 얼굴 일관성 확보 (D66 ①) |
| `b962326` | main | 컷과 연장을 다르게 검사해 오판 제거 (P1-16) + CLI 5단계 |
| `36677de` | main | MCP 한도 우회용 Figma 재개 플레이북 추가 |
| `7f0e45f` | feature | 3D 구도 고정 레이아웃 패스 추가 (D67~D69 기획) |
| `dcf4a46` | feature | 정체성 카드 + 3D 구도 동시 주입 (D68) + CLI 6단계 |

---

## 기획 점검 (사용자 요청 2026-11-21)

| 아이디어 | 기록 | 채택 | 이유 |
|---|---|---|---|
| 1. Blender 3D 구도 + 실사 레이어 | `docs/design/3D_GUIDED_REALISM.md` | **1순위 구현(D67)** | 구도·인물 배치가 일관성 문제의 근본 원인. 무료·로컬. |
| 2. Stable Diffusion | 동 문서 | 병행(D68) | 보유 SDXL/IPAdapter/Wan 자산으로 실사 텍스처·영상화 |
| 3. 정교 3D 모델(게임형) | 동 문서 | **보류(D69/Q9)** | TRELLIS.2·Hunyuan3D 라이선스 확인 전 설치 금지 |

---

## 세션 종료 체크리스트

- [x] 진행분 커밋·푸시 (main 3개)
- [x] ComfyUI 재기동 + `identity-01` 재개
- [x] 기획 3안 기록 + 방향 결정
- [x] 브랜치 생성 + 기능 단위 구현/커밋/푸시 (feature 2개)
- [x] 오프라인 테스트 ALL PASS + CPU 스모키(3씬 0.18초)
- [x] ComfyUI 실 스모키(`guided-01`) — 이중 참조 주입 로그 확인, main 병합 완료(`a346321`)
- [x] `identity-01` 완료 → verify 종합 WARN(FAIL 없음) → WORKLOG 실측 입력
- [x] 레이아웃 라벨 번짐 진단·수정(`ff7031a`) — guided-20은 수정 코드로 재대기
- [x] `guided-01` 완료 → verify → WORKLOG 입력
- [x] `guided-20`(20스텝/수정 도면) 완료 → WORKLOG 입력
- [x] `guided-40`(조명+연장 수정) 완료 → 밝기 FAIL 정정, D71/D71b 원인 분석
- [x] `guided-50`(Blender 3D + D71b) 완료 → verify WARN(FAIL 없음), Blender 3장 확인
- [x] D72 motion-aware 밝기 판정 + 오프라인 테스트 6개 ALL PASS
- [ ] **최종 육안 판정 (사용자 차례)** — `guided-50/final.mp4` + `contact_compare.png`
