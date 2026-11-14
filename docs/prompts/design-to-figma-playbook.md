# 디자인 → Figma 실행 플레이북 (재사용판)

> 씨네목화에서 실제로 돌린 방식을 다른 프로젝트에 그대로 옮기기 위한 문서.
> 첨부: **PRD** + (있으면) **디자인 계획안**. 디자인 계획안이 없으면 이 문서의 Part C-2로 먼저 만든다.

---

## Part A. 쓰는 스킬/도구 목록

### A-1. 실제로 쓴 것 (Figma MCP)

| 종류 | 이름 | 역할 |
|---|---|---|
| 도구 | `whoami` | 플랜·시트·tier 확인 (페이지/모드 한도 파악) |
| 도구 | `create_new_file` | 디자인 파일 생성 → `fileKey` |
| 도구 | `create_session` | 작업 세션 UUID → 이후 모든 파일 도구에 전달 |
| 도구 | `use_figma` | Figma Plugin API 실행 (토큰·컴포넌트·화면 생성의 본체) |
| 도구 | `get_screenshot` / `get_metadata` | 시각/구조 검증 |
| 스킬 문서 | `figma-create-new-file` | 파일 생성 전 필수 |
| 스킬 문서 | `figma-use` | `use_figma` 규칙 (await/return, 0–1 색상, 폰트 로드) |
| 스킬 문서 | `figma-generate-design` | 화면 조립 워크플로 |
| 스킬 문서 | `figma-generate-library` (token-creation 레퍼런스) | 변수 컬렉션·모드·텍스트 스타일 설계 |

### A-2. 의도적으로 안 쓴 것

| 스킬 | 안 쓴 이유 |
|---|---|
| 방향 제시형 디자인 스킬(Hallmark 등) | 방향은 `DESIGN-PLAN.md`가 단일 진실. 테마 재해석으로 톤이 흔들림 |
| 다중 디자인 스킬 동시 사용 | 서로 다른 규칙이 충돌 (사용자 기조: 최소한만) |
| 캠페인/랜딩 빌더 | 제품 UI가 아니라 마케팅 페이지용 |

### A-3. 규칙만 흡수한 것 (Hallmark Floor 8)

1. eyebrow 라벨 금지
2. tracked capitals / small caps 금지
3. 헤드라인 안 단어별 색 변경 금지
4. 이모지 아이콘 금지 (기하 도형/SVG)
5. 보라→파랑 그라데이션 금지
6. 카드 안 카드 금지
7. 화면당 ~80단어 초과 금지
8. `transition: all` · width/height 애니메이션 금지

---

## Part B. 작업 순서 (실제 실행 순서)

```
0. 입력 문서 읽기        PRD + DESIGN-PLAN → 화면 목록·토큰·컴포넌트 확정
1. 플랜 확인            whoami → 페이지 수/모드 수 한도 파악
2. 파일 생성            create_new_file → fileKey
3. 세션 생성            create_session → sessionId
4. 스킬 문서 로드        create-new-file → use → generate-design → generate-library
5. 환경 프로브          페이지 목록 + listAvailableFontsAsync (폰트 폴백 결정)
6. 페이지 구조           한도 내 페이지 수로 압축 (예: 3장)
7. 토큰                 Primitives → Semantic(모드별 컬렉션) → Spacing/Radius → Text Styles
8. Foundations 보드      브랜드 / 컬러 / 타이포 / 스페이싱
9. 컴포넌트             Auto Layout 컴포넌트 세트 (버튼→인풋→상태→챗→카드→내비)
10. 화면                핵심 화면부터 (S1 → S2 → S3 → 나머지)
11. 수치 검증           프레임 밖 넘침/겹침 스캔 → 0으로 수렴
12. Handoff             토큰표·컴포넌트 인벤토리·구현 매핑·열린 이슈
```

### 각 단계의 산출물

| 단계 | 산출물 | 검증 |
|---|---|---|
| 5 | 폰트 폴백 결정문 | 실사용 폰트 스타일 목록 |
| 7 | 변수 컬렉션 + 텍스트 스타일 | 변수 개수, 컬렉션/모드 이름 |
| 8 | 보드 4~5장 | 넘침 0 |
| 9 | 컴포넌트 20~25개 | 이름·크기 목록 |
| 10 | 화면 4~6장 | 넘침 0, 화면당 primary 1개 |
| 12 | 문서 1장 | 토큰 ↔ CSS 변수 매핑 포함 |

### 순서를 지켜야 하는 이유

- 토큰 없이 화면부터 그리면 hex 하드코딩이 생기고 핸드오프가 깨진다.
- 컴포넌트 없이 화면부터 그리면 같은 버튼을 5번 다시 만들게 된다.
- 폰트 프로브를 먼저 해야 스타일 9종을 한 번에 만들 수 있다(나중에 바꾸면 전체 재작업).

---

## Part C. 재사용 프롬프트

### C-1. 메인 프롬프트 (복사해서 사용)

```text
[역할]
너는 시니어 제품 디자이너 + Figma MCP 실행자다. 문서의 방향을 그대로 Figma에 옮긴다.
새로운 디자인 방향을 제안하거나 테마를 새로 뽑지 않는다.

[첨부]
1) PRD: {{PRD_PATH}}
2) 디자인 계획안: {{DESIGN_PLAN_PATH}}   (없으면 "없음"이라고 알려줘)

[먼저 할 일]
- 두 문서를 끝까지 읽고 아래를 뽑아서 나에게 한 번에 보고해라.
  · 화면 목록(ID·이름·목적·핵심 상태)
  · 컬러/타이포/스페이싱/라디우스 토큰
  · 컴포넌트 인벤토리
  · 금지 규칙
- 문서에 없는 값은 임의로 만들지 말고 "미정"으로 표시해 질문해라.

[Figma 실행]
1. whoami로 플랜과 한도(페이지 수, 변수 모드 수)를 확인하고 보고해라.
2. 파일이 없으면 create_new_file, 있으면 그 fileKey를 쓴다. 세션을 만들고 sessionId를 고정한다.
3. use_figma 호출 전에 figma-use / figma-generate-design / figma-generate-library 스킬 문서를 읽는다.
4. 페이지는 한도에 맞춰 압축한다(Starter=3: Design System / Screens / Handoff).
5. 토큰을 먼저 만든다:
   - Primitives(Value) → Semantic Color(모드별 컬렉션) → Spacing → Radius
   - Text Styles는 실제 존재하는 폰트로만 (listAvailableFontsAsync로 확인)
   - 색은 반드시 변수에 바인딩. 하드코딩 hex 금지.
6. Foundations 보드(브랜드/컬러/타이포/스페이싱)를 만든다.
7. Auto Layout 컴포넌트를 만든다. 이름은 `Button/Primary` 처럼 계층형으로.
8. 화면은 핵심부터 만든다. 각 프레임은 1440×900 기준, 120px 간격 그리드.
9. 화면을 만든 직후 넘침/겹침을 수치로 감사해서 0으로 만든다.
10. 마지막에 Handoff 페이지(토큰표·컴포넌트 목록·CSS 변수 매핑·열린 이슈)를 만든다.

[검증 규칙]
- 모든 색: Variable 바인딩 여부 확인
- 모든 프레임: 자식이 프레임 밖으로 나가지 않는지 좌표 계산으로 확인
- 화면당 primary 버튼 1개
- 이모지 아이콘 금지, 보라→파랑 그라데이션 금지, 카드 안 카드 금지
- 숫자·시간·로그는 Mono 스타일

[보고]
- 각 단계마다: 만든 것 / 검증 결과(숫자) / 다음 단계
- 막힌 것은 추측하지 말고 "차단됨 + 사유 + 우회안"으로 보고
```

### C-2. 디자인 계획안이 없을 때 (먼저 실행)

```text
PRD만 첨부했다. 아래 형식으로 `docs/design/DESIGN-PLAN.md`를 먼저 작성해라.
승인 전에는 Figma를 건드리지 않는다.

1. 브랜드 방향 1문장 + 슬로건 + 톤 3단어
2. 컬러 토큰: primitive 이름/hex + semantic 이름(역할) — 다크/라이트 각각
3. 타이포: 스타일명 / 크기 / 행간 / 자간 / 용도 8~10종
4. 스페이싱(4px 그리드) + 라디우스 + 엘리베이션
5. 컴포넌트 인벤토리 20~25개 (이름 / 변형 / 상태)
6. 화면 명세 S0~Sn: ASCII 목업 + 요소 요구표 + 상태(빈/로딩/에러/부분성공)
7. 핵심 플로우 3~4개
8. 모션 스펙
9. 금지·주의 표
10. 리뷰 체크리스트

규칙: 화면당 primary 액션 1개, 정보 6줄 이하, 이모지 아이콘 금지.
```

---

## Part D. 함정 목록 (이번에 실제로 밟은 것)

| 함정 | 증상 | 규칙 |
|---|---|---|
| 플랜 한도 | `createPage: Starter plan only comes with 3 pages` | 실행 전에 whoami로 페이지/모드 한도 확인 |
| 변수 모드 | `addMode` 실패 | 모드 1개면 Light를 **별도 컬렉션**으로 |
| 페이지 전환 | `Setting figma.currentPage is not supported` | `await figma.setCurrentPageAsync(page)` |
| `resize()` | 오토레이아웃 컴포넌트 높이가 10px로 붕괴 | **resize 먼저 → sizingMode 나중** |
| 폰트 | Pretendard 없음 → 스타일 생성 실패 | `listAvailableFontsAsync`로 먼저 확인, 폴백 확정 |
| 텍스트 스타일 | `textStyleId: Required value missing` | 스타일 이름 상수화, 인자 순서 고정 |
| 좌표 기준 | 64px씩 어긋나 하단이 잘림 | 부모 프레임 기준 로컬 좌표로 계산 |
| 클리핑 | 넘친 요소가 화면에서 사라짐 | 생성 직후 넘침 감사 필수 |
| 이미지 검수 | 모델이 스크린샷을 못 볼 수 있음 | 좌표·크기 수치 감사로 대체 |

---

## Part E. 첨부 파일 체크리스트

- [ ] PRD (FR/NFR, 화면 목록, 수용 기준)
- [ ] 디자인 계획안 (토큰, 컴포넌트, 화면 명세)
- [ ] 폰트/브랜드 자산 유무
- [ ] Figma 플랜 (페이지·모드 한도)
- [ ] 기준 해상도 (예: 1440×900) / 다크·라이트 여부
- [ ] 금지 규칙 (있으면 명시)
