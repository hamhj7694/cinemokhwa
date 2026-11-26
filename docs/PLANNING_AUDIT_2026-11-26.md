# 씨네목화 기획·문서·구현 상태 점검 (2026-11-26)

> 기준 저장소: `hamhj7694/cinemokhwa` / `main@e85e86a` (2026-11-24). 이번 검토는 GitHub 코드/문서 **정적 검토**이며 로컬 GPU 재실행·영상 육안 검증을 수행하지 않았다.

## 점검한 근거
`README.md`, `docs/PRD.md`, `docs/DESIGN.md`, `docs/TASKS.md`, `docs/HANDOFF.md`, `docs/HANDOFF_P2.md`, `docs/ENVIRONMENT.md`, `docs/FINAL_REPORT.md`, `docs/WORKLOG.md`, `docs/SESSION_LOG.md`, `docs/design/{3D_GUIDED_REALISM,IDENTITY_FIRST_PIPELINE,DESIGN-PLAN}.md`, `docs/prompts/handoff-qone.md`; `cli.py`, `engine/{config,script,layout3d,character,keyframe,i2v,photo,animate,facegate,verify,assemble}.py`, 기존 테스트 및 스모크 스크립트.

## 진단 결과 (수정 필요도 순)

| ID | 심각도 | 확인된 문제/근거 | 이번 문서 조치 | 향후 코드 조치 |
|---|---|---|---|---|
| A01 | 높음 | `DESIGN.md` 상단 '구현 미착수'·P1/Wan 기준과 신규 P2/LTX 의사결정이 공존 | 문서 우선순위/현행 컨텍스트 분리 | 해당 없음 |
| A02 | 높음 | `TASKS.md`에서 P2=음성·자막, `HANDOFF_P2.md`에서 P2=하이브리드 | 하이브리드는 H0~H6, H-### 티켓 사용 | 새 티켓 경로만 적용 |
| A03 | 높음 | 루트 `AGENTS.md`·`docs/CONTEXT.md` 및 약속된 `ARCHITECTURE.md` 없음. `prompts/handoff-qone.md`는 11/17 상태로 에이전트가 구 계획을 읽음 | 새 `AGENTS.md`, `PROJECT_CONTEXT.md`, P2 문서 세트 제공 | 기존 에이전트 프롬프트 링크 갱신 |
| A04 | 높음 | P1은 **Blender 정지 구도**(layout3d.py: write_still)인데 P2 목표는 전체 움직이는 3D 프리비즈 | 시간별 3D 산출물과 소비 계약 명세 | `engine/previs.py`·모션/패스 렌더 |
| A05 | 높음 | P2 `photo.py`, `animate.py`는 있지만 `cli.py`에 P2 제작 연결 없고 프리비즈/참조/게이트를 end-to-end 연계하지 않음 | stage contract, 통합 책임·순서 정리 | CLI 오케스트레이션 및 회귀 테스트 |
| A06 | 높음 | 기존 `guided-50` 자동 WARN(FAIL 없음)을 성공으로 해석 위험. 사용자 이전 육안은 인물 불일치 지적 | 시각 PASS 필수, 검증과 보고 분리 | 실제 프레임 시퀀스 육안·유사도·궤적 평가 |
| A07 | 높음 | GPU 12GB에서 LTX 25프레임 530.5초; 15초 70분 목표가 실측과 맞지 않음 | 작은 스모크→5초→15초 순서, 속도는 독립 게이트 | 측정 뒤 모델/해상도/분할 선택 |
| A08 | 중간 | 얼굴 카드/IPAdapter는 정체성 보존을 보장하지 못함. P2 레퍼런스 정체성 소유 주체·다인물 고정이 계획 중심 | 단일 기준 자산/ID, 실패 시 차단, LoRA는 별도 실험 | 단일 인물 게이트 우선 구현 |
| A09 | 중간 | 프로토타입 데이터 경로·ID·버전·재개 규칙이 모듈별로 분리되어 통합 계약이 부족 | `P2_CONTRACTS.md` 기준 정의 | 계약 검사·마이그레이션 테스트 |
| A10 | 중간 | README 기술 스택 표에 TTS/립싱크/업스케일/UI 후보가 있어 구현 완료처럼 오인 가능 | README 현행 범위 주의 문구 | 기능 실제 구현 후만 승격 |
| A11 | 중간 | 모델 라이선스/다운로드 제한은 11/21 조사 기록으로 시점 의존적. 상용 허용 여부 확정 위험 | 모델 출처/라이선스 재검증 게이트 | 사용 전 현재 원문·가중치 경로 확인 |
| A12 | 중간 | P1 작업 로그와 P2 계획이 별도인데 통합 변경 승인·파일 소유권 없음 | 역할·PR/통합 규칙·ADR 절차 정의 | 스키마 동결 후 병렬화 |

## 보존할 것과 폐기하지 말 것
- P1 CLI와 Wan/SDXL 3D 가이드 결과는 **재현 가능한 비교 기준(Baseline)**으로 보존한다.
- `WORKLOG`, `FINAL_REPORT`의 실패 기록을 삭제하거나 성공으로 덮지 않는다.
- PRD FR-01~25(장기 제품 요구), 디자인 토큰, 브랜딩, 캐시·재개 및 로컬 우선 원칙 유지.
- P2 `photo.py`, `animate.py`, `facegate.py`, 다운로드 및 스모크 도구를 신규 구현에 재사용하되 통합 검증까지 구현 완료로 판단하지 않는다.

## 정정된 시스템 경계
- **현재(P1):** 주제 → Gemma 장면 → 정면 카드 → Blender 정지 배치 PNG → SDXL 키프레임 → Wan I2V → FFmpeg → 자동 검증/육안 보류.
- **목표(P2):** 주제/참조 → 정체성 자산 → Blender **시간별** 3D 프리비즈/객체 ID/공간 패스 → 실사 앵커 이미지 → LTX 기반 가이드 영상화 → 정체성·동작·품질 검증 → 조립.
- 객체별 사진을 Blender 메시 표면에 직접 UV 매핑하는 구조는 **확정 구현 아님**. 목표는 객체별 이미지 참조와 공간 가이드의 생성형 결합이며, 픽셀·좌표 완전 보존은 별도 실험 문제다.

## 아직 결론내릴 수 없는 사항
- LTX의 프레임 가이드가 **연속 시간 전체**에서 Blender 움직임을 충분히 재현하는가?
- 저VRAM에서 높은 해상도·다중 인물·장면 간 정체성까지 경제적인 속도로 가능한가?
- LoRA·MSR V2·Layout-to-Render를 함께 적용하는 것이 실제 3060 환경에서 가능/유리한가?
- 라이선스와 상업 이용 조건은 재검증 없이 최종 확정할 수 없음.

다음 기준 문서: `P2_REQUIREMENTS.md` → `P2_ARCHITECTURE.md` → `P2_CONTRACTS.md` → `P2_ROADMAP.md` → `P2_TEST_PLAN.md`.
