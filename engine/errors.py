"""오류 규약 — 코드 1개 + 원인 + 다음 행동.

CLI는 이 코드의 접두사로 종료 코드를 정한다. 사용자는 메시지만 읽고
무엇을 해야 하는지 알 수 있어야 한다(수용 기준: "명확한 오류").
"""

from __future__ import annotations

# 접두사 -> 프로세스 종료 코드
EXIT_CODES = {
    "CFG": 3,       # 설정/경로
    "DEP": 4,       # 외부 의존성(ffmpeg 등)
    "MODEL": 5,     # 모델 파일 없음
    "COMFY": 6,     # ComfyUI 통신/실행
    "LLM": 7,       # Ollama 통신/응답
    "FFMPEG": 8,    # 인코딩/조립
    "RENDER": 9,    # 산출물 불완전
    "PROJECT": 10,  # run 디렉터리/상태
    "INTERRUPTED": 130,
}


class CineError(Exception):
    """사용자에게 그대로 보여줄 오류. 트레이스백은 로그에만 남긴다."""

    def __init__(
        self,
        code: str,
        message: str,
        hint: str | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.detail = detail

    @property
    def exit_code(self) -> int:
        return EXIT_CODES.get(self.code.split("-")[0], 1)

    def __str__(self) -> str:
        lines = [f"[{self.code}] {self.message}"]
        if self.hint:
            lines.append(f"  해결: {self.hint}")
        return "\n".join(lines)

    def full(self) -> str:
        """로그 파일에 남길 형태(상세 포함)."""
        out = [str(self)]
        if self.detail:
            out.append("  --- 상세 ---")
            out.extend("  " + line for line in self.detail.strip().splitlines()[:40])
        return "\n".join(out)
