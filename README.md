# 씨네목화 (cinemokhwa)

> **목소리로 짓는 영화**
> 완전 무료 · 무제한 · 로컬 AI 영상 제작 플랫폼

사람의 목소리(녹음)를 출발점으로 삼아, 대본 → 장면화 → 키프레임 → 영상 생성 → 립싱크 → 업스케일 → 조립까지 **영상 픽셀 단위로 직접 생성**하는 로컬 파이프라인입니다.
외부 유료 API 키를 쓰지 않고, 이 PC(RTX 3060 12GB) 한 대에서 동작합니다.

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
