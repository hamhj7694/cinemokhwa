"""대본·스토리보드 — Ollama `gemma4:12b` (D2).

출력은 스키마가 고정된 JSON 하나다. LLM이 규칙을 어기면 1회 교정 요청을 보내고,
그래도 실패하면 임의로 채우지 않고 오류로 멈춘다(수용 기준: 명확한 오류).

씬 1개 = Wan 클립 1개(5초)다. 완성 길이는 씬 수로 환산된다(D50).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import project as project_mod
from .config import Config
from .errors import CineError

# D49 화풍 카탈로그 중 P1이 지원하는 실사 2종. 그림 3종은 M-B에서 추가한다.
STYLES: dict[str, dict[str, str]] = {
    "cinematic": {
        "label": "시네마틱",
        "suffix": (
            "cinematic film still, 35mm film grain, natural skin texture, sharp eyes with "
            "catchlights, warm cinematic colour grade, shallow depth of field, highly detailed, "
            "photorealistic"
        ),
    },
    "natural": {
        "label": "내추럴",
        "suffix": (
            "documentary photograph, natural daylight, true-to-life colours, natural skin "
            "texture, sharp focus, subtle grain, photorealistic"
        ),
    },
}

# Wan은 영상 내 한글·한자를 그리지 못한다(ENVIRONMENT §6). 키프레임 단계에서부터 배제한다.
KEYFRAME_NEGATIVE = (
    "blurry, low quality, watermark, text, letters, signage, signboard, chinese characters, "
    "korean text, logo, extra fingers, deformed hands, warped face, oversaturated, "
    "cartoon, illustration, cgi, 3d render"
)

SYSTEM = """너는 '씨네목화'의 영상 기획자다. 사용자의 주제를 5초 클립 N개로 이루어진 한 편의 짧은 영상으로 바꾼다.

규칙:
1. 정확히 {n}개의 장면을 만든다. 각 장면은 5초짜리 클립 하나에 대응한다.
2. 먼저 "bible"을 정한다. 영상 전체에 공통으로 쓰이는 인물(characters)과 장소(places)를 id와 영어 설명(12단어 이하)으로 적고, "look"에는 시간대·조명·색조를 영어 한 문장(12단어 이하)으로 적는다.
3. 각 장면은 "shot"으로 묶는다. 같은 shot id를 가진 연속 장면은 카메라가 끊기지 않는 한 컷으로 이어진다(같은 shot의 장면은 반드시 붙여서 쓴다). 다른 shot id는 컷 전환이다.
4. 같은 shot 안의 장면은 구도를 바꾸지 마라. 앞 장면의 마지막 화면에서 카메라가 이어지듯 같은 거리·같은 방향으로 서술하고 피사체의 동작만 진행시킨다. 구도·거리·장소가 바뀌면 새 shot으로 나눠라(그 지점이 컷이다).
5. 각 장면의 "anchors"는 bible의 id를 "char:<id>" 또는 "place:<id>" 형식으로 적는다. 그 장면에 실제로 보이는 것만 적는다.
6. "visual"은 키프레임(정지 이미지) 설명이다. 반드시 영어, 35~70단어. 피사체·의상·배경·조명·렌즈·분위기를 구체적으로 쓴다.
7. "motion"은 그 정지 이미지에 입힐 움직임이다. 반드시 영어, 15~40단어. 카메라 이동과 피사체 동작만 쓴다.
8. "narration"은 한국어 내레이션 1~2문장이다. 자막으로도 쓰인다.
9. 화면 안에 글자·간판·로고가 나오게 하지 마라. 이 엔진은 글자를 그리지 못한다.
10. 폭력·선정·실존 인물 실명은 쓰지 않는다.

출력은 아래 JSON 하나만. 설명·마크다운·코드펜스 금지.
{{"title": "제목", "logline": "한 문장 요약",
 "bible": {{"characters": [{{"id": "mina", "desc": "..."}}],
           "places": [{{"id": "alley", "desc": "..."}}],
           "look": "..."}},
 "scenes": [{{"id": 1, "shot": "S1", "anchors": ["char:mina", "place:alley"], "visual": "...", "motion": "...", "narration": "..."}}]}}"""

# 대본 스키마 버전. 올리면 기존 run의 script 단계가 자동으로 다시 돈다.
SCHEMA = 2

EMPTY_BIBLE: dict = {"characters": [], "places": [], "look": ""}


def _entries(raw, field: str) -> list[dict]:
    """bible의 characters/places 배열을 검증한다. id는 소문자로 정규화."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"bible.{field}가 배열이 아닙니다.")
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"bible.{field} 항목이 객체가 아닙니다.")
        ident = str(item.get("id") or "").strip().lower()
        desc = str(item.get("desc") or "").strip()
        if not ident or not desc:
            raise ValueError(f"bible.{field} 항목에 id 또는 desc가 비었습니다.")
        if ident in seen:
            raise ValueError(f"bible.{field} id가 중복됩니다: {ident}")
        seen.add(ident)
        out.append({"id": ident, "desc": desc})
    return out


def _bible(raw) -> dict:
    """bible이 없으면 빈 값. 있으면 형식을 강제한다(임의 보정 금지)."""
    if raw is None:
        return dict(EMPTY_BIBLE)
    if not isinstance(raw, dict):
        raise ValueError("bible이 객체가 아닙니다.")
    return {
        "characters": _entries(raw.get("characters"), "characters"),
        "places": _entries(raw.get("places"), "places"),
        "look": str(raw.get("look") or "").strip(),
    }


def anchor_index(bible: dict) -> dict[str, str]:
    """`char:mina` → 설명. 키프레임 프롬프트 조립용."""
    index: dict[str, str] = {}
    for kind, key in (("char", "characters"), ("place", "places")):
        for item in bible.get(key) or []:
            index[f"{kind}:{item['id']}"] = item["desc"]
    return index


def anchor_text(bible: dict, anchors: list[str]) -> str:
    """앵커 + 공통 look → 영문 프롬프트 조각. 앵커가 없으면 look만."""
    index = anchor_index(bible)
    parts = [index[a] for a in anchors if a in index]
    look = str(bible.get("look") or "").strip()
    if look:
        parts.append(look)
    return ", ".join(parts)



def stage_key(cfg: Config, project: project_mod.Project) -> str:
    return project_mod.digest(
        {
            "stage": "script",
            "schema": SCHEMA,
            "prompt": project_mod.digest(SYSTEM),
            "topic": project.data.get("topic"),
            "target": project.target_seconds,
            "style": project.style,
            "n": cfg.scene_count(project.target_seconds),
            "model": cfg.llm_model,
        }
    )


def _post(path: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url(path)}", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 404:
            raise CineError(
                "LLM-002",
                f"Ollama에 모델이 없습니다: {_model()}",
                hint=f"터미널에서 `ollama pull {_model()}` 을 먼저 실행하세요.",
                detail=body[:800],
            ) from e
        raise CineError("LLM-001", f"Ollama 응답 오류 {e.code}", detail=body[:1200]) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise CineError(
            "LLM-001",
            "Ollama에 연결할 수 없습니다: " + url(""),
            hint="`ollama serve` 가 실행 중인지 확인하세요.",
            detail=str(e),
        ) from e


_URL = ""
_MODEL = ""


def url(path: str) -> str:
    return f"{_URL}{path}"


def _model() -> str:
    return _MODEL


def _chat(cfg: Config, messages: list[dict], temperature: float) -> str:
    global _URL, _MODEL
    _URL, _MODEL = cfg.ollama, cfg.llm_model
    resp = _post(
        "/api/chat",
        {
            "model": cfg.llm_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "keep_alive": "5m",
            "options": {"temperature": temperature, "num_ctx": 8192},
        },
        timeout=900,
    )
    content = (resp.get("message") or {}).get("content", "")
    if not content.strip():
        raise CineError("LLM-003", "LLM이 빈 응답을 보냈습니다.", hint="모델 크기·컨텍스트를 확인하세요.")
    return content


def unload(cfg: Config) -> None:
    """VRAM을 다음 단계(키프레임)에 넘긴다."""
    global _URL, _MODEL
    _URL, _MODEL = cfg.ollama, cfg.llm_model
    try:
        _post("/api/generate", {"model": cfg.llm_model, "keep_alive": 0}, timeout=30)
    except CineError:
        pass


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first < 0 or last <= first:
        raise ValueError("JSON 객체를 찾지 못했습니다.")
    return json.loads(cleaned[first : last + 1])


def _normalize(raw: dict, n: int, clip_seconds: float) -> dict:
    scenes = raw.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes 배열이 없습니다.")
    if len(scenes) < n:
        raise ValueError(f"장면이 {len(scenes)}개뿐입니다(필요 {n}개).")

    bible = _bible(raw.get("bible"))
    index = anchor_index(bible)

    out: list[dict] = []
    last_shot_at: dict[str, int] = {}
    for i, s in enumerate(scenes[:n], start=1):
        if not isinstance(s, dict):
            raise ValueError(f"{i}번 장면이 객체가 아닙니다.")
        visual = str(s.get("visual") or "").strip()
        motion = str(s.get("motion") or "").strip()
        narration = str(s.get("narration") or "").strip()
        if not visual or not motion:
            raise ValueError(f"{i}번 장면에 visual 또는 motion이 비었습니다.")

        shot = str(s.get("shot") or f"S{i}").strip()
        # 한 컷(shot)이 끊겼다 붙으면 체이닝이 엉뚱한 장면을 잇는다.
        if shot in last_shot_at and last_shot_at[shot] != out[-1]["id"]:
            raise ValueError(f"shot {shot}의 장면이 떨어져 있습니다(연속으로 붙여야 함).")
        last_shot_at[shot] = i

        anchors = s.get("anchors") or []
        if not isinstance(anchors, list):
            raise ValueError(f"{i}번 장면의 anchors가 배열이 아닙니다.")
        anchors = [str(a).strip() for a in anchors if str(a).strip()]
        unknown = [a for a in anchors if a not in index]
        if unknown:
            raise ValueError(
                f"{i}번 장면의 anchors가 bible에 없습니다: {', '.join(unknown)}"
                f" (가능: {', '.join(sorted(index)) or '없음'})"
            )

        out.append(
            {
                "id": i,
                "shot": shot,
                "anchors": anchors,
                "visual": visual,
                "motion": motion,
                "narration": narration,
                "seconds": clip_seconds,
            }
        )
    return {
        "schema": SCHEMA,
        "title": str(raw.get("title") or "제목 없음").strip(),
        "logline": str(raw.get("logline") or "").strip(),
        "bible": bible,
        "scenes": out,
    }


def generate(cfg: Config, project: project_mod.Project) -> dict:
    n = cfg.scene_count(project.target_seconds)
    style = STYLES.get(project.style, STYLES["cinematic"])["label"]
    user = (
        f"주제: {project.data.get('topic')}\n"
        f"완성 길이: {project.target_seconds:.0f}초 (5초 클립 {n}개)\n"
        f"화풍: {style} 실사\n"
        f"장면 수: 정확히 {n}개"
    )
    messages = [
        {"role": "system", "content": SYSTEM.format(n=n)},
        {"role": "user", "content": user},
    ]
    raw_text = _chat(cfg, messages, temperature=0.6)

    try:
        result = _normalize(_extract_json(raw_text), n, cfg.clip_seconds)
    except (ValueError, json.JSONDecodeError) as first_error:
        repair = messages + [
            {"role": "assistant", "content": raw_text[:2000]},
            {
                "role": "user",
                "content": (
                    f"위 JSON이 규칙을 어겼다: {first_error}\n"
                    f"정확히 {n}개 장면으로, 스키마만 다시 출력하라. 설명 금지."
                ),
            },
        ]
        raw_text = _chat(cfg, repair, temperature=0.2)
        try:
            result = _normalize(_extract_json(raw_text), n, cfg.clip_seconds)
        except (ValueError, json.JSONDecodeError) as second_error:
            raise CineError(
                "LLM-004",
                "대본 JSON을 2회 시도해도 규칙에 맞추지 못했습니다.",
                hint="더 큰 모델(CINEMOKHWA_LLM=qwen3.8:27b)로 바꾸거나 주제를 짧게 쓰세요.",
                detail=str(second_error),
            ) from second_error

    project.script_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    unload(cfg)
    return result
