# 실행 프롬프트 — 씨네목화 UI/UX 제작 (Figma MCP) v2

> **버전**: v2 · 2026-11-14
> **상태**: 유효. v1의 "페이지 7개 / Pretendard / 다크·라이트 변수 모드 2개" 전제는
> Figma **Starter 플랜(페이지 3개, 컬렉션당 모드 1개)** 에서 성립하지 않아 폐기했다.
> **관계**: 이 문서는 **씨네목화 전용**. 다른 프로젝트에 넘길 일반판은 `design-to-figma-playbook.md`.
> **입력 문서**: `docs/PRD.md`, `docs/design/DESIGN-PLAN.md`, `docs/DESIGN.md`
> **대상 파일**: `씨네목화 — Product Design` · fileKey `pT68j17duxcGL2tdMfdFQd`

---

## 0. 준비 (사람이 먼저)

- [ ] Figma 로그인 + MCP 연결 (`opencode-cli.exe mcp auth figma`)
- [ ] **플랜 한도 확인** — `whoami`로 `tier` / `seat` 확인. Starter면 페이지 3개·모드 1개
- [ ] 파일 생성 또는 기존 `fileKey` 확보
- [ ] 폰트: **Noto Sans KR · JetBrains Mono · Noto Serif KR**
      (Pretendard는 이 환경에 없음 → 대체 확정, 핸드오프에 기록)
- [ ] 한글 콘솔이 깨지는 환경이면 스크립트·로그는 ASCII로

> 한도가 찬 경우 `use_figma`가 `You've reached the Figma MCP tool call limit on the Starter plan`
> 으로 거부된다. `whoami`는 계속 되므로 연결 문제와 구분해서 판단한다.
> 이때는 문서 작업으로 전환하고, 남은 호출을 코드로 준비해둔다.

---

## 1. 실행 규칙 (실패 방지 — 반드시 지킬 것)

| # | 규칙 | 이유 |
|---|---|---|
| 1 | 시작 전 `whoami` → 페이지·모드 한도 보고 | 초과 시 작업 전체가 롤백됨 |
| 2 | 페이지는 **3개**: `01 Design System` / `02 Screens` / `03 Handoff` | Starter 한도 |
| 3 | 라이트 테마는 `Color Light` **별도 컬렉션** | 컬렉션당 모드 1개 |
| 4 | 페이지 전환은 `await figma.setCurrentPageAsync(p)` | `figma.currentPage =` 금지 |
| 5 | 오토레이아웃은 **`resize()` 먼저 → `sizingMode` 나중** | resize가 모드를 FIXED로 덮어씀 |
| 6 | 텍스트 입력 전 `figma.loadFontAsync` 필수 | 미로드 시 예외 |
| 7 | 좌표는 **부모 프레임 로컬 기준**으로 계산 | 화면 절대좌표 혼용 시 64px씩 밀림 |
| 8 | 프레임 생성 직후 **넘침 수치 감사** | `clipsContent` 때문에 넘친 요소가 조용히 사라짐 |
| 9 | 색은 전부 Variable 바인딩 | hex 하드코딩은 핸드오프 불가 |
| 10 | 이모지 아이콘 금지 (기하 도형/SVG) | 디자인 규칙 D46 |
| 11 | 보라→파랑 그라데이션·글래스모피즘·네온 금지 | AI-slop 방지 |
| 12 | primary 버튼은 화면당 1개 | 결정 마비 방지 |
| 13 | 컴포넌트 이름은 `Button/Primary` 형식, 레이어도 의미 있는 이름 | 핸드오프 |
| 14 | 각 STEP 끝에 **만든 것 + 검증 숫자** 보고 후 멈춤 | 폭주 방지 |

---

## 2. 마스터 프롬프트 (그대로 복사)

```text
너는 시니어 프로덕트 디자이너이자 Figma MCP 실행자다.
"씨네목화"의 UI/UX를 Figma 파일에 직접 만든다. 방향은 문서가 정하고, 너는 그대로 옮긴다.

[제품]
씨네목화(cinemokhwa) = 로컬 AI 영상 제작 데스크톱 웹앱.
녹음 또는 대본 → 분석 → 장면화 → 키프레임 → 영상생성 → 립싱크 → 업스케일 → 조립.
슬로건 "목소리로 짓는 영화". 톤: 차분함 · 직조 · 필름 그레인 · 따뜻한 먹색. 다크 기준.
첫 화면은 설정 폼이 아니라 ChatGPT식 대화창이다.

[반드시 읽을 문서]
- docs/PRD.md — 기능 요구, UI 요구, 수용 기준
- docs/design/DESIGN-PLAN.md — 토큰, 컴포넌트, 화면 S0~S5, 상태 매트릭스
- docs/DESIGN.md — D21 스택, D27 다크 기본, D28 shadcn, D35 진행률, D43 자막 프리셋, D46 스킬 정책

[플랜 제약 — 위반하면 작업이 롤백된다]
- Starter: 페이지 3개, 컬렉션당 변수 모드 1개
- 페이지명: 01 Design System / 02 Screens / 03 Handoff
- 라이트는 Color Light 별도 컬렉션

[실행 규칙]
1. 툴 이름을 지어내지 않는다. 사용 가능한 툴을 먼저 확인한다.
2. use_figma 호출 전 figma-use / figma-generate-design / figma-generate-library 문서를 읽는다.
3. 색·간격·타이포는 DESIGN-PLAN의 토큰을 Figma Variables로 등록하고, 모든 레이어를 변수에 바인딩한다.
4. 레이어 이름은 "화면/영역/요소-번호" 형식. "Frame 123" 금지.
5. 오토레이아웃 사용. resize() 후 sizingMode 순서를 지킨다.
6. 폰트는 listAvailableFontsAsync로 확인된 것만. Pretendard 없으면 Noto Sans KR.
7. 프레임 생성 직후 자식이 프레임 밖으로 나가는지 좌표로 감사하고 0으로 만든다.
8. 한국어 라벨. 번역투 금지. 이모지 아이콘 금지.
9. 보라 그라데이션·글래스모피즘·네온·3단 그림자 금지.
10. primary 버튼은 화면당 1개.
11. 각 STEP이 끝나면 "만든 것 / 검증 숫자 / 다음 STEP"만 보고하고 멈춘다.
12. 확실하지 않으면 만들지 말고 질문한다.

[프레임 규격]
- Desktop 1440×900. 마진 32, 12컬럼 감각, 4px 스페이싱 그리드.
- 화면 간 간격 120, 좌상단 기준 그리드 배치.

먼저 ① whoami 결과와 한도 ② 사용 가능한 툴 목록 ③ 3페이지 계획만 보고하고 멈춰라.
```

---

## 3. 단계별 프롬프트

### STEP 0 — 프로브 (필수)

```text
아직 아무것도 만들지 말고 조사만 해라.

1. whoami → tier, seat, plans[].key
2. 파일의 페이지 목록
3. listAvailableFontsAsync → Noto Sans KR / JetBrains Mono / Noto Serif KR / Pretendard 존재 여부와 스타일 목록
4. 결과를 표로 보고하고, 페이지 수·모드 수 한도에 맞춘 계획을 제시해라.

보고: 한도, 폰트 대체 여부, 페이지 계획, 위험 요소.
```

### STEP 1 — 페이지 골격

```text
페이지를 정확히 3개로 맞춘다. 초과 생성 금지.
1. 01 Design System
2. 02 Screens
3. 03 Handoff

기존 페이지가 3개보다 많으면 이름을 재사용하고, 남는 페이지는 만들지 않는다.
`await figma.setCurrentPageAsync(page)`로 전환한다.
보고: 페이지 목록과 각 페이지 프레임 수.
```

### STEP 2 — 토큰

```text
DESIGN-PLAN의 토큰을 Figma Variables + Text Styles로 만든다.

컬렉션
- Primitives (Value): cotton/seed/thread/ink/paper/state 계열 원시 hex
- Color (Dark): semantic 이름을 Primitives에 **별칭(VARIABLE_ALIAS)** 으로 연결
- Color Light (Light): 같은 semantic 이름, 라이트 원시값에 별칭
- Spacing (Value): 4/8/12/16/20/24/32/40/48/64
- Radius (Value): sm 6 / md 10 / lg 16 / xl 24 / pill 999

텍스트 스타일 9종: Display / H1 / H2 / H3 / Body / Body Strong / Caption / Mono / Serif
폰트: Noto Sans KR(UI), JetBrains Mono(수치·로그), Noto Serif KR(에디토리얼)

필수 semantic: bg/base, bg/surface, bg/elevated, bg/input, bg/hover,
border/subtle, border/strong, text/primary, text/secondary, text/tertiary,
text/on-accent, accent, accent/hover, success, warning, danger, info,
brand/cotton, brand/seed, brand/thread

금지: hex 직접 입력, 모드 2개 생성(addMode).

보고: 컬렉션 목록과 모드, COLOR/FLOAT 변수 개수, 텍스트 스타일 목록.
```

### STEP 3 — Foundations 보드 (01 Design System)

```text
1440 폭 보드 4장을 세로로 배치한다. 넘침 0.

F0 Brand: 마크(기하 도형) + 워드마크 + 슬로건 + 뿌리 문장
F1 Color: Primitive 스와치(이름 + hex) + Semantic 스와치(Dark, 6열)
F2 Type: 9종 샘플 + 스타일명 + 스펙(크기/행간/자간)
F3 Space & Radius: 스페이싱 바 + 라디우스 사각형

모든 색은 변수 바인딩. 도형으로만 아이콘 표현(이모지 금지).
보고: 보드별 크기와 넘침 검사 결과(0이어야 함).
```

### STEP 4 — 컴포넌트 1 (버튼·입력·상태)

```text
01 Design System에 Auto Layout 컴포넌트를 만든다.
이름은 계층형(Button/Primary). 각 컴포넌트 아래 Mono 라벨로 스펙을 적는다.

Button/Primary · Secondary · Ghost · Danger · Icon(40x40)
Input/Text(320) · Textarea(480x96) · Select(240)
Badge/Neutral · Badge/Accent · Progress/Bar · Toggle/On · Avatar/Default · Toast/Info

주의: resize() 먼저, sizingMode 나중. 높이가 10px로 붕괴하면 순서 실수다.
보고: 컴포넌트명과 실제 크기 목록(높이가 10이면 실패).
```

### STEP 5 — 컴포넌트 2 (대화·카드·내비)

```text
이어서 만든다.
Chat/User(우측 버블) · Chat/Assistant(아바타 + 액션 칩) · Composer/Default(mic이 생성보다 앞)
Card/Scene(16:9) · Card/Project · Indicator/Steps · Empty/Scenes · Nav/Sidebar Item

Card/Scene: 썸네일 + 타임코드 + 내레이션 1줄 + 상태 배지. 정보 6줄 초과 금지.
보고: 컴포넌트명과 크기.
```

### STEP 6 — S1 기획 (최우선)

```text
02 Screens에 "S1 · 기획 — 첫 화면" 프레임(1440×900, 다크)을 만든다.

상단: 마크 + 씨네목화 + 탭(기획/제작/결과, 기획 활성) + 우측 테마/설정/도움말
좌 55% (대화):
- AI 인사 + 추천 칩 3개
- 사용자 버블(우측): "제주 바다 다큐 30초, 차분한 나레이션으로. 새벽 파도부터 시작해줘."
- AI 응답: 6장면 초안 요약 + 액션 칩 2개
- 진행 중 표시(인라인 프로그레스)
- 하단 고정 Composer: placeholder + 16:9 / 1080p / Wan 2.2 칩 + mic + 전송
우 45% (설정 + 스토리보드):
- 장르 / 목소리 / 화풍 Segmented(실사 활성) / 비율 / 길이 / 자막 / BGM
- 캐릭터 행 + [목화 창고]
- 스토리보드 3장면(완료/완료/생성 중)
- 하단 바: "6장면 · 30.4초 · 예상 55분" + [스토리보드 확정] + [영상 생성]

좌표는 부모 프레임 로컬 기준. Composer는 좌측 프레임 하단에서 24px 띄운다.
보고: 프레임 크기, 주요 영역 좌표, 넘침 검사 0.
```

### STEP 7 — S2 제작

```text
"S2 · 제작 — 목화 스튜디오"(1440×900, 다크).

- 경로 Segmented: S 대본+녹음(활성) | D 대화 | T 텍스트→TTS
- 오디오 카드: [녹음][업로드][TTS] + "00:31.4 / 00:32.0" + 파형(결정적 높이 배열) + 구간 마커 7개
- 장면 표 5행: 번호·구간·대사·화자·립싱크·상태(완료/완료/생성 중/대기/대기), 생성 중 행에만 [재시도]
- 8단계 스테퍼: 녹음→분석→장면화→키프레임(현재)→영상→립싱크→업스케일→조립
- 진행: "33%" + 바 + "예상 55분 · 경과 18분 · 남은 ~37분"
- 하단 바: [로그] + [일시정지] + [생성 계속] primary 1개

보고: 표 행 수, 스테퍼 단계 수, 넘침 0.
```

### STEP 8 — S3 · S0 · S4 · S5

```text
네 화면을 만든다.

S3 결과: 좌 플레이어(16:9) + 스크러버 + 장면 블록 6개(3번 선택) + [재생성][편집][삭제] /
         우 내보내기(프리셋·자막 번인|사이드카·예상 용량·[내보내기] primary·자막 스타일 5칩·BGM·덕킹)
S0 시작: 히어로 슬로건 + 환경 점검 5행(실패 1행은 danger + [다시 받기]) + [새 프로젝트] primary + 최근 프로젝트
S4 목화 창고: 캐릭터 카드 4열(3:4) + 우 인스펙터(시드·화풍·레퍼런스·버전 타임라인 v3/v2/v1)
S5 설정: 외관/언어/경로/기본값/데이터. 하단 버튼이 프레임을 넘지 않게 본문 높이를 먼저 계산한다.

배치: S1(0,0) S2(1560,0) S3(0,1020) S4(1560,1020) S0(0,2040) S5(1560,2040)
보고: 화면별 넘침 검사 결과(전부 0이어야 함).
```

### STEP 9 — 상태 · 플로우 (02 Screens 안 섹션)

```text
페이지를 추가하지 말고 02 Screens 하단에 섹션으로 만든다.

상태 4종 (각 1440×900 또는 축약 720×450):
- S1 빈 대화: 추천 프롬프트 3개만 있는 상태
- S2 실패: 실패 행 + 사유 + [재시도] + "이어서 생성"
- S3 내보내기 중: 진행률 + 취소
- 공통: Toast 3종(info/success/danger)

플로우 F1~F4: 각 단계 프레임 썸네일 + 화살표 + 한 줄 설명.
F1 첫 영상: S0 → S1(3턴) → S2(녹음) → S2(생성) → S3 → 내보내기
F2 숏폼: S1(숏폼) → TTS → 생성 → S3
F3 장면 재생성: S3 → 장면 선택 → 재생성 → 반영
F4 실패 복구: S2 실패 → 사유 → 이어서 생성

보고: 만든 상태 프레임 수, 플로우 수.
```

### STEP 10 — Handoff (03 Handoff)

```text
03 Handoff에 문서 프레임 1장을 만든다. 폭 1440, 높이는 내용에 맞춰 자동 계산.

1. 제품 한 줄 + 경계(로컬·무료·픽셀 생성)
2. 화면 목록 S0~S5 (한 줄 설명)
3. 토큰: 컬렉션·변수 개수·타입 스케일·폰트 대체 사실
4. 컴포넌트 인벤토리
5. 구현 매핑: React+Vite+TS / Tailwind / shadcn/ui / Zustand / SSE / FastAPI
   토큰 → CSS 변수 이름 규칙(--color-bg-base 등)
6. 접근성: focus 2px accent, 최소 클릭 32px, 대비 4.5:1, prefers-reduced-motion
7. 열린 이슈: 라이트 컬렉션 분리, 썸네일 플레이스홀더, 폰트 대체

마지막에 전체 요약: 페이지·프레임 목록, 미완성 항목과 이유, 문서와 달라진 결정.
```

---

## 4. 운용 팁 (실제 오류 기반)

| 증상 | 원인 | 지시 |
|---|---|---|
| `Starter plan only comes with 3 pages` | 페이지 초과 | "페이지를 3개로 줄이고 나머지는 같은 페이지 섹션 프레임으로 배치해라." |
| `addMode` 실패 | 컬렉션당 모드 1개 | "라이트를 별도 컬렉션으로 만들어라." |
| `Setting figma.currentPage is not supported` | 구식 API | "`await figma.setCurrentPageAsync(page)`를 써라." |
| 컴포넌트 높이가 10px | resize가 sizingMode 덮어씀 | "resize 먼저, sizingMode 나중으로 순서를 바꿔라." |
| `textStyleId: Required value missing` | 스타일 이름/인자 순서 오류 | "스타일 이름을 상수로 검증하고, 존재하는 이름만 넘겨라." |
| 하단 요소가 잘림 | 부모 프레임 로컬좌표 혼용 | "부모 기준 로컬 좌표로 다시 계산하고 넘침을 0으로 만들어라." |
| 툴이 없다고 함 | 추측 호출 | "사용 가능한 툴 목록을 먼저 출력하고, 없는 툴은 대안을 제안해라." |
| 레이어 이름이 Frame 123 | 이름 미지정 | "'화면/영역/요소' 규칙으로 일괄 변경해라." |
| AI-slop처럼 보임 | 금지 규칙 미적용 | "보라 그라데이션·글래스·이모지 아이콘을 제거하고 D46을 재적용해라." |
| 호출 한도 초과 | Starter MCP 한도 | "문서 작업으로 전환하고, 남은 호출을 코드로 준비해라." |

---

## 5. 완료 정의 (3페이지 기준)

- [ ] 페이지 3개: Design System / Screens / Handoff
- [ ] 토큰: 컬렉션 5개, COLOR 변수, FLOAT 변수, 텍스트 스타일 9종
- [ ] Foundations 보드 4장, 넘침 0
- [ ] 컴포넌트 22개 이상, Auto Layout, 높이 붕괴 0
- [ ] 화면 S0~S5 다크 6장, 1440×900, 넘침 0
- [ ] 상태 4종 + 플로우 F1~F4
- [ ] Handoff 1장 (토큰 표 + shadcn 매핑 + CSS 변수 규칙 + 열린 이슈)
- [ ] 금지 규칙 위반 0건 (이모지 아이콘·보라 그라데이션·카드 안 카드)
- [ ] 화면당 primary 1개
- [ ] (선택) S1 라이트 1장 — `Color Light` 바인딩
