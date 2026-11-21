# 최종 보고서 (씨네목화)

> 항상 최신 상태로 갱신한다. 최종 갱신: 2026-11-21 (guided-40 → guided-50 순차 렌더 중)
> 상세 작업 기록: [`SESSION_LOG.md`](SESSION_LOG.md)

---

## 1. 한 줄 요약

D66 ①(정면 카드)·P1-16(컷/연장 검증)을 main에 커밋·푸시했고, 사용자가 제시한 3가지
기획 아이디어를 모두 기록한 뒤 **1+2 조합(3D 레이아웃 → 실사 레이어)**을 기능 단위로
구현·푸시·main 병합했습니다. 조명 불일치·연장 씬 간섭을 순차 수정했고, **Blender 4.5 LTS를
직접 설치해 3D 레이아웃 기본 백엔드로 연결(D70)**했습니다.
현재 `guided-40`(조명+연장 수정, CPU 로드)과 `guided-50`(Blender 백엔드)이 순차 렌더 중이며,
완료 시 verify·최종 비교 후 결과만 보고드립니다.

---

## 2. 현재 상태 표

| 구분 | 상태 | 상세 |
|---|---|---|
| D66 ① 정면 카드 | ✅ | main `2b37b5b` |
| P1-16 검증 | ✅ | main `b962326` |
| Figma 재개 문서 | ✅ | main `36677de` |
| 3D 가이드 기획(D67~D69) | ✅ | feature `7f0e45f` — 3안 모두 기록, main 병합 완료 |
| D67 3D 레이아웃 엔진 | ✅ | 결정론적 Scene3D, CPU 블록아웃 3씬 0.18초, Blender export |
| D68 이중 참조 | ✅ | IPAdapter(얼굴) + img2img(구도) 동시 주입, 6단계 |
| 레이아웃 라벨 번짐 수정 | ✅ | main `ff7031a` — 라벨 제거·denoise 0.70, 실 ComfyUI 진단 반영 |
| 조명·장소 불일치 수정 | ✅ | main `5d61132` — 사용자 육안 피드백 반영. 장소·노출 상시 고정, 암부 표현 치환 |
| feature → main 병합 | ✅ | main `a346321` 푸시 완료 |
| 오프라인 테스트 | ✅ ALL PASS | 결정성·투사·캐시·이중참조 노드, py_compile |
| `identity-01` (Before) | ✅ | 43.2분, 14.54초, verify WARN(FAIL 없음) |
| `guided-01` (6스텝) | ⚠️ 완료 | 12.7분, 이중 참조 실 주입 확인. 구버전 도면 라벨 번짐으로 verify FAIL → 원인 수정됨 |
| 조명 균일 확인 | ✅ | guided-20 실측 Yavg 107/113/105 — 장면 간 밝기 차이 해소 |
| 연장 씬 레이아웃 수정 | ✅ | main `30efa2a` — scene 2는 도면 없이 앞 클립 체이닝(D63 보강) |
| `guided-20` (20스텝) | ⚠️ 완료 | 58.7분, 라벨 번짐 해결. verify scene 2 선명도 0.636 FAIL |
| `guided-30` | ⏹ 중단 | guided-40에 흡수(중복) |
| `guided-40` (중간 검증) | ⚠️ 완료 | 75.8분. 개별 클립 PASS였으나 **씬 간 밝기 차이 81.97 → FAIL**(Yavg 34/35/116). 숫자 PASS만으로 통과 불가 확인 |
| D71 밝기 일관성 | ✅ | main `5e6889d` — verify에 씬 간 밝기 검사(WARN 25/FAIL 50) 추가, 키프레임 후보 선택에 밝기 기준 반영 |
| D70 Blender 백엔드 | ✅ | main `5a3c151` — 4.5.16 LTS 설치, 3씬 렌더 78초, 라플라시안 5~15 |
| `guided-50` (Blender 검증) | ⏳ 대기 | guided-40 종료 후 자동 시작. **Blender 최종 판정 대상** |
| Q9 정교 3D 모델 | ⏹ 조사 완료 | Hunyuan3D 한국 제외 / TRELLIS.2 의존성 제약 → 부적합, 설치 안 함(D69) |

---

## 3. 사용자 확인이 필요한 것

| # | 항목 | 경로 / 상태 |
|---|---|---|
| 1 | **① Before** (1280×704/20스텝, 3D 가이드 없음) | `C:\Users\mbc\mokhwa\work\identity-01\final.mp4` — 14.54초 / 7.99MB / verify WARN |
| 2 | **② After 저해상도** (832×480/6스텝, 구버전 도면) | `C:\Users\mbc\mokhwa\work\guided-01\final.mp4` — 14.54초 / 7.47MB. 라벨 번짐 있어 참고용 |
| 3 | **③ After 본검증** (1280×704/20스텝, 수정 도면) | `C:\Users\mbc\mokhwa\work\guided-20\final.mp4` — 라벨 번짐 해결. scene 2 선명도 FAIL |
| 4 | **④ 최종 검증** (1280×704/20스텝, 조명 고정+연장 수정) | `C:\Users\mbc\mokhwa\work\guided-40\final.mp4` — 생성 중. **최종 판정 대상** |
| 5 | 3D 구도 도면 | `C:\Users\mbc\mokhwa\work\guided-40\layouts\layout_01~03.png` — 라벨 제거된 수정본 |

> **비교 포인트**: ①에서 얼굴/배경이 바뀌던 컷이 고정되는지, 그리고 **세 장면의 골목 밝기가 같은지** 보면 됩니다.
> ②는 라벨 번짐, ③은 연장 씬 간섭, ④는 씬 간 밝기 차이(81.97)가 있어 **최종 판정은 ⑤ guided-50**으로 해주세요.
> 다 같은 대본·같은 인물 카드로 만들어 차이가 수정 효과입니다.
> 육안 비교표: `C:\Users\mbc\mokhwa\work\contact_compare.png` (`python tools/contact_sheet.py`로 갱신 가능).

---

## 4. 커밋/푸시 이력

| 브랜치 | 해시 | 기능 |
|---|---|---|
| main | `2b37b5b` | D66 ① 정면 카드 |
| main | `b962326` | P1-16 검증 + CLI 5단계 |
| main | `36677de` | Figma 재개 플레이북 |
| feature | `7f0e45f` | D67~D69 기획 + 레이아웃 엔진 |
| feature | `dcf4a46` | D68 이중 참조 + 6단계 파이프라인 |
| feature | `66662bc`·`580e2a5`·`cfe5ef9`·`f76fb13`·`32d5355`·`4288537` | 문서 동기화·튜닝·스모키·본검증 안내 |
| main | `a346321` | feature → main 병합 |
| main | `ff7031a` | 라벨 번짐 수정(denoise 0.70) |
| main | `80bb198`·`7bff526` | 진단·진행 상태 문서화 |

---

## 5. 기획 채택 결과

| 아이디어 | 판단 |
|---|---|
| 1. Blender 3D 구도 + 실사 레이어 | 채택 — Blender 미설치라 순수 Python 블록아웃으로 구현, export 경로 마련 |
| 2. Stable Diffusion | 채택 — 기존 SDXL/Wan/IPAdapter 재사용 |
| 3. 정교 3D 모델(게임형) | 보류 — Q9 라이선스 확인 전 설치 금지 |

---

> 이 문장은 작업이 끝날 때마다 다시 쓴다. 이전 내용은 `SESSION_LOG.md`에 남는다.
