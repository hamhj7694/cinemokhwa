"""ComfyUI HTTP 클라이언트.

P1이 쓰는 표면은 4개뿐이다: `/prompt`(등록) · `/history/{id}`(완료 확인) ·
`/upload/image`(키프레임 주입) · `/free`(VRAM 반환).

산출물은 같은 PC의 `ComfyUI/output/`에서 직접 읽는다(경로 복사·다운로드보다 빠르고
P0에서 검증된 방식). 파일이 없으면 `/view`로 내려받아 대체한다.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .config import Config
from .errors import CineError

START_HINT = (
    r"ComfyUI를 시작하세요: "
    r"& 'C:\Users\mbc\mokhwa\ComfyUI_windows_portable\python_embeded\python.exe' "
    r'-s "C:\Users\mbc\mokhwa\ComfyUI_windows_portable\ComfyUI\main.py" '
    r"--windows-standalone-build --disable-auto-launch --port 8188"
)


class Comfy:
    def __init__(self, cfg: Config, quiet: bool = False) -> None:
        self.cfg = cfg
        self.quiet = quiet
        self.client_id = uuid.uuid4().hex

    # ------------------------------------------------------------- plumbing
    def _url(self, path: str) -> str:
        return f"{self.cfg.host}{path}"

    def _get(self, path: str, timeout: float = 20) -> dict:
        try:
            with urllib.request.urlopen(self._url(path), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise CineError(
                "COMFY-002",
                f"ComfyUI 응답 오류 {e.code} ({path})",
                detail=body[:1200],
            ) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CineError(
                "COMFY-001",
                f"ComfyUI에 연결할 수 없습니다: {self.cfg.host}",
                hint=START_HINT,
                detail=str(e),
            ) from e

    def _post(self, path: str, payload: dict, timeout: float = 60) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(path), data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            if not raw.strip():
                return {}  # /free 등은 빈 본문을 돌려준다
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise CineError(
                "COMFY-002",
                f"ComfyUI가 작업을 거부했습니다 ({e.code})",
                hint="노드 이름·모델 파일명을 확인하세요(engine/workflows 생성부 참조).",
                detail=body[:2000],
            ) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CineError(
                "COMFY-001",
                f"ComfyUI에 연결할 수 없습니다: {self.cfg.host}",
                hint=START_HINT,
                detail=str(e),
            ) from e

    # ------------------------------------------------------------- public
    def alive(self) -> dict:
        return self._get("/system_stats", timeout=8)

    def version(self) -> str:
        try:
            return str(self.alive().get("system", {}).get("comfyui_version", "?"))
        except CineError:
            return "?"

    def submit(self, workflow: dict) -> str:
        resp = self._post("/prompt", {"prompt": workflow, "client_id": self.client_id})
        return str(resp["prompt_id"])

    def wait(self, prompt_id: str, timeout_s: float, label: str) -> dict:
        """완료까지 대기. 오류/시간 초과는 CineError로 올린다."""
        t0 = time.time()
        last_note = 0.0
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout_s:
                raise CineError(
                    "COMFY-003",
                    f"{label} 시간 초과 ({timeout_s / 60:.0f}분)",
                    hint="ComfyUI 로그(logs\\comfyui.log)에서 마지막 노드를 확인하세요.",
                )
            record = self._get(f"/history/{prompt_id}")
            if prompt_id in record:
                rec = record[prompt_id]
                status = rec.get("status", {})
                if status.get("status_str") == "error":
                    raise CineError(
                        "COMFY-004",
                        f"{label} 실행 실패",
                        hint="아래 상세의 노드 오류를 확인하세요.",
                        detail=json.dumps(status.get("messages", []), ensure_ascii=False)[:2500],
                    )
                return rec
            if not self.quiet and elapsed - last_note >= 60:
                print(f"      … {label} {elapsed / 60:.1f}분 경과", flush=True)
                last_note = elapsed
            time.sleep(5)

    def run(self, workflow: dict, label: str, timeout_s: float) -> dict:
        prompt_id = self.submit(workflow)
        if not self.quiet:
            print(f"      큐 등록 {prompt_id[:8]} · {label}", flush=True)
        return self.wait(prompt_id, timeout_s, label)

    def free_memory(self) -> None:
        """모델 언로드(D: 모델 수명 관리). 실패는 무시 — 다음 단계가 알아서 올린다."""
        try:
            self._post("/free", {"unload_models": True, "free_memory": True}, timeout=15)
        except CineError:
            pass

    # ------------------------------------------------------------- images
    def upload_image(self, path: Path) -> str:
        """`/upload/image` → LoadImage가 읽을 수 있는 이름을 돌려준다."""
        boundary = "----cinemokhwa" + uuid.uuid4().hex
        payload = path.read_bytes()
        parts = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n",
            payload,
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode(),
        ]
        req = urllib.request.Request(
            self._url("/upload/image"),
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                info = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            raise CineError(
                "COMFY-005",
                "키프레임 업로드 실패",
                hint="ComfyUI가 실행 중인지 확인하세요.",
                detail=str(e),
            ) from e
        name = info.get("name") or path.name
        sub = info.get("subfolder") or ""
        return f"{sub}/{name}" if sub else name

    def outputs(self, record: dict) -> list[dict]:
        """history record → 이미지 참조 목록(filename/subfolder/type)."""
        refs: list[dict] = []
        for node in (record.get("outputs") or {}).values():
            # SaveImage → images, SaveVideo → gifs (ComfyUI 관례)
            for key in ("images", "gifs", "videos"):
                for item in node.get(key, []) or []:
                    if item not in refs:
                        refs.append(item)
        return refs

    def download(self, ref: dict, dest: Path) -> Path:
        query = urllib.parse.urlencode(
            {
                "filename": ref.get("filename", ""),
                "subfolder": ref.get("subfolder", ""),
                "type": ref.get("type", "output"),
            }
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(self._url(f"/view?{query}"), timeout=120) as r:
                dest.write_bytes(r.read())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            raise CineError(
                "COMFY-006",
                f"산출물 내려받기 실패: {ref.get('filename')}",
                detail=str(e),
            ) from e
        return dest

    def materialize(self, record: dict, dest_dir: Path | None = None) -> list[Path]:
        """참조 → 실제 파일 경로. output/에 있으면 그대로, 없으면 다운로드."""
        paths: list[Path] = []
        for ref in self.outputs(record):
            on_disk = (
                self.cfg.comfy_output
                / str(ref.get("subfolder") or "")
                / str(ref.get("filename") or "")
            )
            if on_disk.exists() and on_disk.stat().st_size > 0:
                paths.append(on_disk)
            elif dest_dir is not None:
                paths.append(self.download(ref, dest_dir / str(ref["filename"])))
            else:
                raise CineError(
                    "RENDER-001",
                    f"산출물 파일이 없습니다: {on_disk}",
                    hint="ComfyUI 출력 폴더가 engine 설정과 같은지 확인하세요.",
                )
        return sorted(paths, key=lambda p: p.name)


def frame_pattern(files: list[Path]) -> str:
    """연속 프레임 목록 → ffmpeg `%05d` 패턴. 규칙이 다르면 RENDER 오류."""
    if not files:
        raise CineError("RENDER-002", "프레임이 0장입니다.", hint="SaveImage 노드 출력을 확인하세요.")
    m = re.match(r"^(.*?)(\d+)(_?\.png)$", files[0].name)
    if not m:
        raise CineError("RENDER-002", f"프레임 이름 규칙을 해석할 수 없습니다: {files[0].name}")
    stem, digits, ext = m.group(1), m.group(2), m.group(3)
    width = len(digits)
    for f in files:
        if not re.match(rf"^{re.escape(stem)}\d{{{width}}}{re.escape(ext)}$", f.name):
            raise CineError(
                "RENDER-002",
                f"프레임 이름이 섞였습니다: {f.name}",
                hint="한 씬의 프레임은 같은 접두사·자릿수여야 합니다.",
            )
    return str(files[0].parent / f"{stem}%0{width}d{ext}")
