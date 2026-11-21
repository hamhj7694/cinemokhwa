#!/usr/bin/env python
"""씨네목화 CLI — M-A(실사) 코어 파이프라인.

  mokhwa env check
  mokhwa status
  mokhwa make --topic "비 오는 서울 골목" --seconds 15
  mokhwa make --topic "..." --seconds 15 --plan     (예상 시간만)
  mokhwa make --run-id 20261116-101500             (이어서/재개)
  mokhwa make --run-id ... --scene 2 --force        (장면 1개만 다시)
  mokhwa verify --run-id 20261116-101500            (품질 수치 측정)
  mokhwa batch --file plan.json

종료 코드: 0 성공 / 3 설정 / 4 의존성 / 5 모델 / 6 ComfyUI / 7 LLM /
          8 FFmpeg / 9 산출물 / 10 프로젝트 / 130 중단
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import assemble, character, i2v, keyframe, layout3d, script, verify  # noqa: E402
from engine import project as project_mod  # noqa: E402
from engine.comfy import Comfy  # noqa: E402
from engine.config import Config  # noqa: E402
from engine.errors import CineError  # noqa: E402


# --------------------------------------------------------------------- output
def _init_console() -> None:
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def say(text: str = "") -> None:
    print(text, flush=True)


def step(index: int, total: int, title: str) -> None:
    say(f"\n[{index}/{total}] {title}")


def skip(title: str) -> None:
    say(f"      건너뜀 — {title} (캐시 유효)")


def human(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}분 {s:02d}초" if m else f"{s}초"


def estimate_minutes(cfg: Config, scenes: int, characters: int = 1) -> float:
    """P0 실측 기반. 카드 4장 + 키프레임 4장×24초 + I2V (0.72×steps+3.6)분/클립."""
    cards = characters * len(keyframe.SEEDS) * 0.4
    keyframes = scenes * len(keyframe.SEEDS) * 0.4
    clips = scenes * (0.72 * cfg.i2v_steps + 3.6)
    return cards + keyframes + clips + 1.0


def chain_sources(project: project_mod.Project) -> dict[int, int | None]:
    """같은 shot에서 앞 장면 id. 다른 shot이면 None(=컷). D63."""
    previous: dict[int, int | None] = {}
    by_shot: dict[str, int] = {}
    for s in project.scenes():
        sid = int(s["id"])
        shot = str(s.get("shot") or f"S{sid}")
        previous[sid] = by_shot.get(shot)
        by_shot[shot] = sid
    return previous


# --------------------------------------------------------------------- pipeline
def run_pipeline(
    cfg: Config,
    project: project_mod.Project,
    *,
    force: bool = False,
    only_scene: int | None = None,
) -> Path:
    total = 6
    t_all = time.time()
    comfy = Comfy(cfg)

    # 1. 대본 -------------------------------------------------------------
    step(1, total, "대본·스토리보드 (gemma4:12b)")
    key = script.stage_key(cfg, project)
    if project.done("script", key) and project.script_path.exists() and not force:
        skip("script.json")
    else:
        project.begin("script", key)
        t = time.time()
        try:
            data = script.generate(cfg, project)
        except CineError as exc:
            project.fail("script", str(exc))
            raise
        project.finish("script", key, seconds=round(time.time() - t, 1))
        project.log_line(f"script ok {time.time() - t:.1f}s")
        say(f"      완료 — {data['title']} · 장면 {len(data['scenes'])}개 ({human(time.time() - t)})")

    scenes = project.scenes()
    if only_scene is not None:
        scenes = [s for s in scenes if int(s["id"]) == only_scene]
        if not scenes:
            raise CineError("PROJECT-003", f"장면 {only_scene}이(가) 대본에 없습니다.")
        force = True

    # 2. 캐릭터 카드 (D66 ①) -----------------------------------------------
    step(2, total, "캐릭터 기준 이미지 (정면 카드 · D66 ①)")
    ckey = character.stage_key(cfg, project)
    chars = project.bible().get("characters") or []
    cards_ready = all(character.card_path(project, c["id"]).exists() for c in chars)
    if project.done("characters", ckey) and cards_ready and not force:
        skip(f"{len(chars)}장 · bible.ref 유지")
        character.generate_all(cfg, comfy, project)  # 캐시여도 ref 재기입
    else:
        project.begin("characters", ckey)
        t = time.time()
        try:
            cinfo = character.generate_all(cfg, comfy, project, force=force)
        except CineError as exc:
            project.fail("characters", str(exc))
            raise
        project.finish("characters", ckey, seconds=round(time.time() - t, 1), items=cinfo)
        project.log_line(f"characters ok {time.time() - t:.1f}s")
        if cinfo:
            say(f"      완료 — {len(cinfo)}명 ({human(time.time() - t)})")
        else:
            say("      인물 없음 — 카드 생성 생략")
    comfy.free_memory()

    # 3. 3D 레이아웃 (D67) -------------------------------------------------
    step(3, total, "3D 레이아웃 (결정론적 구도 · 블록아웃)")
    lkey = project_mod.digest(
        {"stage": "layout", "keys": [
            layout3d.stage_key(project, s, i)
            for i, s in enumerate(project.scenes())
        ]}
    )
    layouts_ready = all(
        layout3d.layout_path(project, s["id"]).exists() for s in project.scenes()
    )
    if project.done("layout", lkey) and layouts_ready and not force:
        skip(f"{len(project.scenes())}장 · 구도 캐시")
    else:
        project.begin("layout", lkey)
        t = time.time()
        linfo = []
        for i, s in enumerate(project.scenes()):
            p, meta = layout3d.generate(
                project, s, sequence=i,
                width=cfg.width, height=cfg.height, force=force,
            )
            linfo.append({"scene": s["id"], **meta})
        project.finish("layout", lkey, seconds=round(time.time() - t, 1), items=linfo)
        project.log_line(f"layout ok {time.time() - t:.1f}s")
        say(f"      완료 — {len(linfo)}장 ({human(time.time() - t)}) · CPU만 사용")

    # 4. 키프레임 ---------------------------------------------------------
    step(4, total, "키프레임 (SDXL 4시드 → 중앙 선명도 최고 · 3D 구도 주입)")
    chain_of = chain_sources(project)
    stage_ids = {int(s["id"]) for s in scenes}
    # 참조 대상은 대본만 보고 정한다(파일 존재 여부에 캐시 키가 흔들리지 않게).
    refs: dict[int, dict | None] = {}
    for s in project.scenes():
        sid = int(s["id"])
        # 같은 shot의 연장은 앞 클립 프레임을 이미 start_image로 쓰므로 참조가 불필요하다.
        if chain_of.get(sid) is not None or cfg.kf_reference == "none":
            refs[sid] = None
            continue
        card = character.card_for(project, s)  # D66 ①: 정면 카드를 1순위로
        if card is not None:
            path, label = card
            refs[sid] = {
                "kind": "card",
                "label": label,
                "digest": project_mod.file_digest(path),
            }
            continue
        target = keyframe.reference_target(project, s)  # 카드 없으면 종전 규칙
        if target is None:
            refs[sid] = None
            continue
        tid, label = target
        digest = ""
        if tid not in stage_ids:   # 이번 실행에서 다시 만들지 않는 대상만 파일 해시 반영
            path = keyframe.reference_path(project, tid)
            digest = project_mod.file_digest(path) if path else "none"
        refs[sid] = {"kind": "keyframe", "target": tid, "label": label, "digest": digest}
    kf_keys = [
        keyframe.stage_key(
            cfg, project, s,
            ref_target=(
                refs[int(s["id"])]["target"]
                if refs[int(s["id"])] and refs[int(s["id"])]["kind"] == "keyframe"
                else None
            ),
            ref_digest=refs[int(s["id"])]["digest"] if refs[int(s["id"])] else None,
            ref_card=(
                refs[int(s["id"])]["label"]
                if refs[int(s["id"])] and refs[int(s["id"])]["kind"] == "card"
                else None
            ),
            layout_digest=project_mod.file_digest(layout3d.layout_path(project, s["id"])),
        )
        for s in scenes
    ]
    key = project_mod.digest({"stage": "keyframes", "items": kf_keys})
    kf_ready = all(project.keyframe_path(s["id"]).exists() for s in scenes)
    key_changed = not project.done("keyframes", key)
    if not key_changed and kf_ready and not force:
        skip(f"{len(scenes)}장")
    else:
        project.begin("keyframes", key)
        t = time.time()
        meta = []
        try:
            for s in scenes:
                info_ref = refs[int(s["id"])]
                ref, ref_label = (None, "")
                if info_ref:
                    if info_ref["kind"] == "card":
                        ref = character.card_by_label(project, info_ref["label"])
                        ref_label = info_ref["label"]
                    else:
                        ref = keyframe.reference_path(project, info_ref["target"])
                        ref_label = info_ref["label"]
                path, info = keyframe.generate(
                    cfg, comfy, project, s,
                    reference=ref, reference_label=ref_label,
                    layout=layout3d.layout_path(project, s["id"]),
                    force=force or key_changed,
                )
                meta.append({"scene": s["id"], **info})
                if info.get("cached"):
                    note = "캐시"
                else:
                    note = f"seed={info['seed']} 중앙={info['center_sharpness']}"
                    if info.get("reference"):
                        note += f" · 참조 {info['reference']}({info['reference_mode']})"
                say(f"      장면 {s['id']:02d} — {note}")
        except CineError as exc:
            project.fail("keyframes", str(exc))
            raise
        project.finish("keyframes", key, seconds=round(time.time() - t, 1), items=meta)
        project.log_line(f"keyframes ok {time.time() - t:.1f}s")
        say(f"      완료 — {human(time.time() - t)}")
    comfy.free_memory()

    # 5. 클립 -------------------------------------------------------------
    step(5, total, f"영상 클립 (Wan I2V · {cfg.i2v_steps}스텝 · {cfg.width}×{cfg.height})")
    chain_of = chain_sources(project)
    clip_keys = []
    chain_dirs: dict[int, Path | None] = {}
    for s in scenes:
        sid = int(s["id"])
        kf = project.keyframe_path(sid)
        if not kf.exists():
            raise CineError("PROJECT-004", f"키프레임이 없습니다: {kf.name}", hint="2단계를 먼저 실행하세요.")
        prev = chain_of.get(sid)
        if prev is None:
            prev_key = None
            chain_dirs[sid] = None
        else:
            prev_clip = project.clip_path(prev)
            prev_key = project_mod.file_digest(prev_clip) if prev_clip.exists() else "pending"
            chain_dirs[sid] = project.frames / f"scene_{prev:02d}"
        clip_keys.append(i2v.stage_key(cfg, project, s, kf, prev_key))
    key = project_mod.digest({"stage": "clips", "items": clip_keys})
    clips_ready = all(project.clip_path(s["id"]).exists() for s in scenes)
    if project.done("clips", key) and clips_ready and not force:
        skip(f"{len(scenes)}개")
    else:
        project.begin("clips", key)
        t = time.time()
        meta = []
        try:
            for idx, s in enumerate(scenes, start=1):
                chain_dir = chain_dirs[int(s["id"])]
                tag = " · 연장" if chain_dir is not None else ""
                say(f"      장면 {s['id']:02d} 시작{tag} (예상 {(0.72 * cfg.i2v_steps + 3.6):.0f}분)")
                path, info = i2v.generate(
                    cfg,
                    comfy,
                    project,
                    s,
                    project.keyframe_path(s["id"]),
                    force=force,
                    chain_from=chain_dir,
                )
                meta.append({"scene": s["id"], **info})
                if info.get("cached"):
                    note = "캐시"
                else:
                    note = f"{info['frames']}프레임 {human(info['seconds'])}"
                    if info.get("seam_mae") is not None:
                        note += f" · 이음새 MAE {info['seam_mae']}"
                say(f"      장면 {s['id']:02d} 완료 — {note} · 누적 {human(time.time() - t)}")
                if idx == 1:
                    comfy.free_memory()
        except CineError as exc:
            project.fail("clips", str(exc))
            raise
        project.finish("clips", key, seconds=round(time.time() - t, 1), items=meta)
        project.log_line(f"clips ok {time.time() - t:.1f}s")
        say(f"      완료 — {human(time.time() - t)}")
    comfy.free_memory()

    # 6. 조립 -------------------------------------------------------------
    step(6, total, f"조립 (크로스페이드 {cfg.crossfade_seconds}초 · CRF{cfg.crf})")
    all_clips = [project.clip_path(s["id"]) for s in project.scenes()]
    missing = [c.name for c in all_clips if not c.exists()]
    if missing:
        raise CineError(
            "RENDER-005",
            f"조립에 필요한 클립이 없습니다: {', '.join(missing)}",
            hint="장면별 클립을 먼저 생성하세요.",
        )
    key = project_mod.digest(
        {
            "stage": "assemble",
            "clips": [project_mod.file_digest(c) for c in all_clips],
            "crossfade": cfg.crossfade_seconds,
            "crf": cfg.crf,
        }
    )
    if project.done("assemble", key) and project.final.exists() and not force:
        skip("final.mp4")
    else:
        project.begin("assemble", key)
        t = time.time()
        try:
            out, durations = assemble.concat(
                all_clips, project.final, cfg, crossfade=cfg.crossfade_seconds
            )
            timeline = assemble.write_timeline(
                project, all_clips, durations, cfg, crossfade=cfg.crossfade_seconds
            )
        except CineError as exc:
            project.fail("assemble", str(exc))
            raise
        project.finish("assemble", key, seconds=round(time.time() - t, 1))
        project.log_line(f"assemble ok {time.time() - t:.1f}s")
        say(f"      완료 — {out.name} · {timeline.name} ({human(time.time() - t)})")

    project.log_line(f"pipeline done total={time.time() - t_all:.1f}s")
    return project.final


# --------------------------------------------------------------------- commands
def cmd_env(args: argparse.Namespace) -> int:
    cfg = Config()
    failures = 0
    say("씨네목화 환경 점검")
    say("=" * 58)

    say(f"설치 경로       {cfg.root}")
    if not cfg.root.exists():
        failures += 1
        say("  ✘ 폴더가 없습니다 (D55: C:\\Users\\mbc\\mokhwa)")

    try:
        ver = Comfy(cfg).version()
        say(f"ComfyUI         OK · {cfg.host} · v{ver}")
    except CineError as exc:
        failures += 1
        say(f"ComfyUI         ✘ {exc.message}")
        say(f"  해결: {exc.hint}")

    say("모델")
    for label, path in cfg.model_files():
        if path.exists():
            say(f"  ✔ {label:<16} {path.stat().st_size / 1e9:6.2f} GB  {path.name}")
        else:
            failures += 1
            say(f"  ✘ {label:<16} 없음  {path}")

    try:
        ff = cfg.ffmpeg()
        say(f"FFmpeg          OK · {ff}")
        if not cfg.ffprobe().exists():
            failures += 1
            say("  ✘ ffprobe.exe가 같은 폴더에 없습니다")
    except CineError as exc:
        failures += 1
        say(f"FFmpeg          ✘ {exc.message}")

    try:
        import urllib.request

        with urllib.request.urlopen(f"{cfg.ollama}/api/tags", timeout=8) as r:
            tags = json.loads(r.read().decode("utf-8"))
        names = [m.get("name", "") for m in tags.get("models", [])]
        if cfg.llm_model in names:
            say(f"Ollama          OK · {cfg.ollama} · {cfg.llm_model}")
        else:
            failures += 1
            say(f"Ollama          ✘ 모델 없음: {cfg.llm_model}")
            say(f"  해결: ollama pull {cfg.llm_model}")
            say(f"  설치됨: {', '.join(names) or '없음'}")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        say(f"Ollama          ✘ 연결 실패: {cfg.ollama}")
        say(f"  해결: ollama serve  ({exc})")

    try:
        free_gb = shutil.disk_usage(cfg.root).free / 1e9
        mark = "✔" if free_gb > 20 else "✘"
        if free_gb <= 20:
            failures += 1
        say(f"디스크 여유      {mark} {free_gb:.1f} GB")
    except OSError:
        pass

    say("=" * 58)
    if failures:
        say(f"결과: 실패 {failures}건 — 위 해결 항목을 처리하세요.")
        return 1
    say("결과: 모두 통과. `mokhwa make --topic \"...\" --seconds 15 --plan` 으로 예상 시간을 확인하세요.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cfg = Config()
    runs = project_mod.list_runs(cfg.work)
    if not runs:
        say(f"실행 기록이 없습니다: {cfg.work}")
        return 0
    say(f"{'run_id':<18} {'길이':>5} {'완성':>4}  단계")
    say("-" * 74)
    for r in runs:
        stages = " ".join(f"{k}:{v}" for k, v in r["stages"].items()) or "-"
        say(
            f"{r['run_id']:<18} {str(r['target_seconds']):>5} "
            f"{'✔' if r['final'] else '·':>4}  {stages}"
        )
    return 0


def cmd_make(args: argparse.Namespace) -> int:
    cfg = Config()
    cfg.ensure_dirs()

    project: project_mod.Project | None = None
    if args.run_id:
        project = project_mod.load(cfg.work, args.run_id)
        say(f"실행 이어서: {project.run_id} · {project.dir}")
        stored = project.data.get("params") or {}
        for key in ("width", "height", "i2v_steps", "crossfade_seconds", "crf"):
            if key in stored:
                setattr(cfg, key, stored[key])
    else:
        if not args.topic:
            raise CineError("CFG-001", "새 실행에는 --topic이 필요합니다.")
        seconds = float(args.seconds or 15)
        if seconds < cfg.clip_seconds:
            raise CineError("CFG-002", f"완성 길이는 최소 {cfg.clip_seconds:.0f}초입니다.")

    # CLI에 명시한 값이 저장값을 이긴다.
    if args.steps is not None:
        cfg.i2v_steps = int(args.steps)
    if args.crossfade is not None:
        cfg.crossfade_seconds = float(args.crossfade)
    if args.width:
        cfg.width = int(args.width)
    if args.height:
        cfg.height = int(args.height)

    if project is None:
        project = project_mod.create(
            cfg.work,
            args.topic,
            float(args.seconds or 15),
            style=args.style,
            params={
                "width": cfg.width,
                "height": cfg.height,
                "i2v_steps": cfg.i2v_steps,
                "crossfade_seconds": cfg.crossfade_seconds,
                "crf": cfg.crf,
                "steps_keyframe": cfg.keyframe_steps,
            },
        )
        say(f"실행 생성: {project.run_id} · {project.dir}")

    scenes = cfg.scene_count(project.target_seconds)
    n_chars = len(project.bible().get("characters") or []) or 1
    est = estimate_minutes(cfg, scenes, n_chars) + 0.1  # D67 레이아웃(CPU)
    say(
        f"계획: {scenes}씬 × {cfg.clip_seconds:.0f}초 · {cfg.width}×{cfg.height} · "
        f"{cfg.i2v_steps}스텝 · 예상 {est:.0f}분"
    )
    if est > 70:
        say(f"  ⚠ 70분 예산 초과 예상({est:.0f}분). --steps 20 또는 --seconds를 줄이세요.")

    if args.plan:
        say("\n--plan: 생성하지 않았습니다. 위 수치로 판단하세요.")
        return 0

    final = run_pipeline(
        cfg,
        project,
        force=args.force,
        only_scene=args.scene,
    )
    duration = assemble.probe_duration(final, cfg)
    say("\n" + "=" * 58)
    say(f"완성: {final}")
    say(f"길이: {human(duration)} · 타임라인: {project.timeline.name}")
    say(f"재개: mokhwa make --run-id {project.run_id}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    cfg = Config()
    project = project_mod.load(cfg.work, args.run_id)
    stored = project.data.get("params") or {}
    for key in ("width", "height", "i2v_steps", "crossfade_seconds", "crf"):
        if key in stored:
            setattr(cfg, key, stored[key])

    result = verify.run(cfg, project)
    if args.json:
        say(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["overall"] != "FAIL" else 9

    say(f"품질 측정 — {project.run_id} · 클립 {len(result['clips'])}개 · "
        f"{result['sample_every']}프레임마다 표본")
    say("")
    say(f"{'scene':>5} {'경계':>4} {'기준':>11} {'YAVGsd':>7} {'YDIF':>6} "
        f"{'MAE':>6} {'SSIM':>6} {'팔레트':>6} {'드리프트':>8}  verdict")
    say("-" * 88)
    for row in result["clips"]:
        mae = "-" if row["first_frame_mae"] is None else f"{row['first_frame_mae']:.2f}"
        ssim = "-" if row["ssim"] is None else f"{row['ssim']:.2f}"
        pal = "-" if row["palette_l1"] is None else f"{row['palette_l1']:.1f}"
        boundary = "연장" if row["boundary"] == "extend" else "컷"
        mark = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}[row["verdict"]]
        say(f"{row['scene']:>5} {boundary:>4} {row['reference']:>11} "
            f"{row['yavg_std']:>7.2f} {row['ydif_median']:>6.2f} {mae:>6} "
            f"{ssim:>6} {pal:>6} {row['end_drift']:>8.1f}  {mark} {row['verdict']}"
            + ("   (wide)" if row["wide_shot"] else ""))

    notes = [(r["scene"], k, v) for r in result["clips"]
             for k, v in r["verdicts"].items() if v != "PASS"]
    if notes:
        say("")
        say("기준 미달 항목")
        for scene_id, item, verdict in notes:
            say(f"  장면 {scene_id:02d}  {item:<14} {verdict}")
        say("")
        say("  WARN = 장면 의도(원경·뒷모습·보케)로 설명 가능. 육안 확인.")
        say("  FAIL = 결함 가능성. 해당 장면 재생성 권장:")
        say(f"    .\\mokhwa.cmd make --run-id {project.run_id} --scene N --force")

    say("")
    say(f"저장: {result['_path']}")
    say(f"종합: {result['overall']}")
    return 0 if result["overall"] != "FAIL" else 9


def cmd_batch(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        raise CineError("CFG-003", f"배치 파일이 없습니다: {path}")
    jobs = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", [])
    if not jobs:
        raise CineError("CFG-003", "배치 파일에 jobs가 비었습니다.")
    failures = 0
    for i, job in enumerate(jobs, start=1):
        say(f"\n### 배치 {i}/{len(jobs)} — {job.get('topic', '')[:40]}")
        ns = argparse.Namespace(
            topic=job.get("topic"),
            seconds=job.get("seconds", 15),
            run_id=None,
            style=job.get("style", "cinematic"),
            steps=job.get("steps", 20),
            crossfade=job.get("crossfade", 0.3),
            width=job.get("width"),
            height=job.get("height"),
            force=False,
            scene=None,
            plan=False,
        )
        try:
            cmd_make(ns)
        except CineError as exc:
            failures += 1
            say(f"  실패: {exc}")
    say(f"\n배치 종료 — 성공 {len(jobs) - failures}/{len(jobs)}")
    return 1 if failures else 0


# --------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mokhwa", description="씨네목화 — 로컬 AI 영상 제작")
    sub = parser.add_subparsers(dest="command", required=True)

    p_env = sub.add_parser("env", help="환경 점검")
    p_env.add_argument("action", choices=["check"])
    p_env.set_defaults(func=cmd_env)

    p_status = sub.add_parser("status", help="실행 목록")
    p_status.set_defaults(func=cmd_status)

    p_make = sub.add_parser("make", help="영상 1편 생성(또는 재개)")
    p_make.add_argument("--topic", help="주제(새 실행)")
    p_make.add_argument("--seconds", type=float, default=15, help="완성 길이(초)")
    p_make.add_argument("--run-id", help="이어서 실행할 run_id")
    p_make.add_argument("--style", default="cinematic", choices=sorted(script.STYLES))
    p_make.add_argument("--steps", type=int, default=None, help="I2V 스텝(20~25, 기본 20)")
    p_make.add_argument("--width", type=int)
    p_make.add_argument("--height", type=int)
    p_make.add_argument("--crossfade", type=float, default=None, help="전환 길이(초, 0=하드컷, 기본 0.3)")
    p_make.add_argument("--force", action="store_true", help="캐시 무시")
    p_make.add_argument("--scene", type=int, help="지정 장면만 재생성")
    p_make.add_argument("--plan", action="store_true", help="예상 시간만 출력")
    p_make.set_defaults(func=cmd_make)

    p_verify = sub.add_parser("verify", help="품질 수치 측정(PRD 13.5)")
    p_verify.add_argument("--run-id", required=True)
    p_verify.add_argument("--json", action="store_true", help="JSON으로 출력")
    p_verify.set_defaults(func=cmd_verify)

    p_batch = sub.add_parser("batch", help="여러 편 순차 생성")
    p_batch.add_argument("--file", required=True)
    p_batch.set_defaults(func=cmd_batch)
    return parser


def main(argv: list[str] | None = None) -> int:
    _init_console()
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except CineError as exc:
        say()
        print(exc.full(), file=sys.stderr, flush=True)
        return exc.exit_code
    except KeyboardInterrupt:
        say("\n중단되었습니다. 이어서 하려면 --run-id로 다시 실행하세요.")
        return 130
    except Exception:  # noqa: BLE001
        print("\n예상하지 못한 오류입니다. 아래 내용을 보관하세요.", file=sys.stderr, flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
