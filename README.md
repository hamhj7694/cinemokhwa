# 씨네목화 (cinemokhwa)

> **2026-11-26 최신 기획 안내:** 개발·에이전트 시작점은 [AGENTS.md](AGENTS.md) → [문서 지도](docs/DOCS_INDEX.md) → [P2 요구사항](docs/P2_REQUIREMENTS.md) → [통합 아키텍처](docs/P2_ARCHITECTURE.md) → [작업 로드맵](docs/P2_ROADMAP.md). 아래 README의 영상 파이프라인·성능 예시는 **현재 P1 기반 구현/시험 기록**이고, 새 P2 하이브리드는 독립 모듈 단계로 **미통합**이다.

> **목소리로 짓는 영화**
> 외부 유료 영상 생성 API를 사용하지 않는 로컬 AI 영상 제작 파이프라인 — 개발·실험 중

사람의 목소리(녹음)를 출발점으로 대본 → 장면화 → 키프레임 → 영상 생성 → 후처리 → 조립으로 이어지는 **로컬 제작 파이프라인을 단계적으로 구현하는 프로젝트**입니다. 현재는 단일 제작 모드(M-A 실사)의 CLI 코어와 실험 결과가 중심이며, 모든 제작 모드·웹 UI·립싱크·업스케일의 완성이나 무제한 성능을 뜻하지 않습니다.

---


## 2026-11-28 P2 프리비즈 개선 사항 (계획 / 미구현)

- 샷마다 **`coarse`(기본 실험 가설), `joint_lite`(필요 접촉·관절), `none`(비교), `geometry_rerender`(연구)** 중 필요한 최소한의 3D 형태를 선택하는 **Adaptive Previs** 설계 추가.
- Blender control tracks(카메라/root/접촉/ID)는 정밀하게 보존하되, 모델에 보여줄 도형은 단순화. 얼굴·의상·감정은 사진 참조·실사 키프레임·프롬프트가 담당.
- 현재 P1은 Blender **정지 3D 구도 PNG**이고, P2 풀 프리비즈 + LTX 효과는 **아직 통합 구현·육안 검증 전**.
- [새 설계](docs/design/ADAPTIVE_PREVIS.md) · [근거 결정](docs/adr/ADR-001-adaptive-previs.md) · [A/B 검증](docs/experiments/P2_PREVIS_VALIDATION.md) · [전체 MD 32개 점검](docs/PLANNING_REVIEW_2026-11-28.md).

## 포트폴리오 한눈에

**문제 정의:** AI로 영상 장면을 하나씩 만드는 과정에서는 캐릭터·장소·조명·구도의 일관성과 재생성 비용을 관리하기 어렵습니다. 이를 기획자가 반복 실행·수정할 수 있는 제작 파이프라인으로 연결하려는 개인 개발 프로젝트입니다.

| 항목 | 구현·검증 근거 |
|---|---|
| 현재 구현 | CLI 기반 M-A 실사 제작: 대본 구조화 → 장면·참조 정보 → SDXL 키프레임 → Wan I2V 클립 → FFmpeg 조립 |
| 반복 제작 | run ID, 장면별 상태·입력 해시, 실패·부분 재개, 단계별 시간 기록 |
| 품질 개선 | 장면 간 밝기 차이와 선명도·드리프트 등을 분리 검사하고 3D 블록아웃·조명 앵커를 실험 |
| 실제 실험 | `guided-50`: 3씬·14.54초·1280×704 결과물을 57.0분에 생성. 최종 검사는 **WARN**(씬 2 드리프트), 전면 품질 통과가 아님 |
| 남은 과제 | UI 설계, 모드 확장, 일관성·품질의 반복 검증, 제작 시간·하드웨어 제약 |

**강조할 역량:** 제작 자동화 파이프라인 설계, 실패 원인 분석, 실측 로그 기반 개선. **현재 완성형 영상 플랫폼이나 상용 서비스는 아닙니다.** 실험 결과는 [WORKLOG](docs/WORKLOG.md), 실제 구현 범위는 [engine/README.md](engine/README.md)에서 확인할 수 있습니다.

*UI/Figma의 실제 검증된 화면 캡처가 확인되기 전까지 다른 프로젝트의 이미지를 사용하지 않습니다. 향후 이 프로젝트의 Figma 파일 또는 로컬 생성 영상 프레임을 확인한 후 이 구역에 추가합니다.*

---


## 브랜드 계층

| 역할 | 이름 | 핸들 |
|---|---|---|
| 제품/앱 | **씨네목화** | `cinemokhwa` |
| 캠페인/커뮤니티 | 목화씨네 영화관 | `mokhwa` |
| 편집/제작 화면 | 목화 스튜디오 | — |
| 캐릭터·소스 보관소 | 목화 창고 | — |
| CLI | `mokhwa` | — |

- 뿌리: **목화** = 목(목소리) + 화(영화)
- 뿌리 문장: "말이 씨가 되어 영화가 된다"
- 줄임말 금지: 제품은 항상 `씨네목화`, 캠페인은 항상 `목화씨네 영화관`

---

## 문서 지도

| 문서 | 상태 | 목적 |
|---|---|---|
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | ✅ 최신 (2026-11-17) | **인수인계** — 목적·현재 상태·실행법·함정·용어를 한 문서에 |
| [`docs/WORKLOG.md`](docs/WORKLOG.md) | ✅ 최신 | **작업·실측 로그** — run별 조건·단계별 소요·결과·모델 성능 기준값 |
| [`docs/DESIGN.md`](docs/DESIGN.md) | ✅ 완료 (D1~D66) | 단일 설계 기준서 — 결정 로그·파이프라인·데이터 구조·브랜딩 |
| [`docs/PRD.md`](docs/PRD.md) | ✅ v0.3 | 제품 요구사항 — 대상·시나리오·기능(FR 25)·비기능(NFR)·수용 기준 |
| [`docs/design/DESIGN-PLAN.md`](docs/design/DESIGN-PLAN.md) | ⚠️ 모드 UI 미반영 | Figma 비주얼/UI·UX 기획 — 화면·토큰·컴포넌트·플로우 |
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | ✅ P0 완료 (v0.3) | 설치 경로·모델 목록(모드별)·실측 성능·설치 함정 |
| [`engine/`](engine/README.md) | ✅ P1 코어 (M-A) | 구현체 — `mokhwa.cmd` CLI · 대본→키프레임→I2V→조립 · 모듈 규격 |
| [`docs/prompts/figma-uiux.md`](docs/prompts/figma-uiux.md) | ✅ v2 | Big Pickle + Figma MCP 실행 프롬프트 |
| `docs/ARCHITECTURE.md` | ⏸ 대기 | 컴포넌트·인터페이스 상세 |
| `docs/TASKS.md` | ✅ P0~P7 (55티켓) | 티켓 분해 + DoD + 게이트 매핑 |
| `docs/AGENTS.md` · `docs/CONTEXT.md` | ⏸ 대기 | Qwen 에이전트 지침 / 세션 주입 요약 |
| `docs/prompts/P*.md` | ⏸ 대기 | 단계별 구현 프롬프트 |
| [`tools/contact_sheet.py`](tools/contact_sheet.py) | ✅ 신규 | **육안 판정용** — run별 3씬 대표 프레임을 한 장의 PNG 비교표로 생성 |

> 육안 비교표 실행: `python tools/contact_sheet.py --runs identity-01 guided-40 guided-50`
> (아직 `final.mp4`가 없는 run은 자동 건너뜀. 결과는 `C:\Users\mbc\mokhwa\work\contact_*.png`)

---

## 개발 순서 (확정)

```
상세기획  →  PRD 작성  →  비주얼 디자인 · UI/UX (Figma 우선)  →  구현 (P1 코어)
   ✅            ✅           ⚠️ Starter 호출 한도(Q8) 대기 중        🔄 진행 중
```

- 기획·설계·문서: **Big Pickle** (이 세션)
- 구현 코딩: 로컬 **`qwen3-coder:30b`** (OpenCode ↔ Ollama) + 설계 변경·디버깅은 Big Pickle (D47)
- **D39: 사용자 승인 전 구현 착수 금지** — P1은 D62로 승인됨

---

## 기술 스택 (요약)

| 계층 | 선택 |
|---|---|
| 영상 생성 | ComfyUI Portable + Wan 2.2 TI2V-5B FP8 |
| 대본 LLM | `gemma4:12b` (Ollama) |
| 키프레임 | SDXL 3종(실사 2 · 애니 1) + 프롬프트 레시피(동화·수채) + IPAdapter |
| TTS / 전사 | MeloTTS(KR) / faster-whisper large-v3-turbo |
| 립싱크 | MuseTalk · LatentSync 1.5 · SadTalker |
| 업스케일 | Real-ESRGAN 4x → 1920×1080 |
| 조립 | FFmpeg |
| 웹 | React + Vite + TS · Tailwind/shadcn · Zustand · SSE · FastAPI |

상세 근거는 `docs/DESIGN.md` §4(결정 로그) · §6(모델 스택) 참조.

---

## 제약 (고정)

- Windows 10 Pro · i5-10500 · 32GB RAM · **RTX 3060 12GB** · 관리자 권한 없음
- VRAM 12GB → **GPU 작업 직렬화**(한 번에 모델 하나만 로드)
- 네이티브 생성 1280×704 → 1080p는 Real-ESRGAN 업스케일로 달성
- 클립 5초 단위 · 영상 내 텍스트 렌더 불가(자막으로 해결) · 기본 오디오 없음
