import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

import config
from app.agents.prompt_agent import build_video_prompts
from app.agents.storyboard_agent import build_storyboard
from app.extractor.ppt_extractor import extract_ppt_text
from app.agents.psd_agent import build_psd
from app.agents.story_plan_agent import build_story_plan
from app.schemas.models import PresentationSemanticDocument, StoryPlanDocument
from app.utils.file_utils import ensure_dir
from app.utils.json_utils import load_json, save_json
from app.utils.markdown_utils import save_video_prompts_markdown

BASE_DIR = Path(__file__).resolve().parent
INPUT_UPLOAD_DIR = BASE_DIR / "input" / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
ALLOWED_DOWNLOADS = {
    "extracted_slides.json",
    "psd.json",
    "story_plan.json",
    "storyboard.json",
    "video_prompts.json",
    "video_prompts.md",
}

JOB_STEPS = [
    ("queued", "Queued", 2),
    ("extract", "Extracting PPT text", 15),
    ("psd", "Building semantic document", 35),
    ("story_plan", "Planning the story", 55),
    ("storyboard", "Writing storyboard", 75),
    ("prompts", "Generating video prompts", 92),
    ("done", "Done", 100),
]
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "app" / "web" / "templates"),
    static_folder=str(BASE_DIR / "app" / "web" / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024


def _json_response(payload: Any, status: int = 200):
    return app.response_class(
        json.dumps(payload, ensure_ascii=False, indent=2),
        status=status,
        mimetype="application/json",
    )


def _safe_run_id(value: str) -> str:
    cleaned = secure_filename(value.strip())
    if not cleaned:
        cleaned = f"run_{int(time.time())}"
    return cleaned


def _run_dir(run_id: str) -> Path:
    run_dir = (OUTPUT_DIR / _safe_run_id(run_id)).resolve()
    output_root = OUTPUT_DIR.resolve()
    if output_root not in run_dir.parents and run_dir != output_root:
        raise ValueError("Invalid run id")
    return run_dir


def _load_optional_json(run_dir: Path, name: str):
    path = run_dir / name
    if not path.exists():
        return None
    return load_json(path)


def _load_run(run_id: str) -> dict[str, Any]:
    run_dir = _run_dir(run_id)
    if not run_dir.exists():
        raise FileNotFoundError(run_id)

    files = sorted(path.name for path in run_dir.iterdir() if path.is_file())
    markdown_path = run_dir / "video_prompts.md"
    payload = {
        "run_id": run_dir.name,
        "path": str(run_dir),
        "files": files,
        "extracted": _load_optional_json(run_dir, "extracted_slides.json"),
        "psd": _load_optional_json(run_dir, "psd.json"),
        "story_plan": _load_optional_json(run_dir, "story_plan.json"),
        "storyboard": _load_optional_json(run_dir, "storyboard.json"),
        "video_prompts": _load_optional_json(run_dir, "video_prompts.json"),
        "video_prompts_md": markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else "",
    }
    return payload


def _run_summary(run_id: str) -> dict[str, Any]:
    data = _load_run(run_id)
    extracted = data.get("extracted") or {}
    story_plan = data.get("story_plan") or {}
    storyboard = data.get("storyboard") or {}
    prompts = data.get("video_prompts") or {}
    return {
        "run_id": run_id,
        "path": data["path"],
        "slide_count": extracted.get("slide_count", 0),
        "segments": len(story_plan.get("segments", [])),
        "scenes": len(storyboard.get("scenes", [])),
        "prompts": len(prompts.get("prompts", [])),
        "files": data["files"],
    }


def _job_snapshot(job_id: str) -> dict[str, Any] | None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def _set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.update(updates)
        job["updated_at"] = time.time()


def _set_job_step(job_id: str, step: str, message: str, progress: int) -> None:
    _set_job(job_id, step=step, message=message, progress=progress)


def _run_pipeline_job(job_id: str, pptx_path: Path, output_dir: Path, provider: str) -> None:
    try:
        _set_job(job_id, status="running", step="extract", message="Extracting PPT text", progress=15)
        extracted = extract_ppt_text(pptx_path)
        extracted_path = output_dir / "extracted_slides.json"
        save_json(extracted_path, extracted)

        _set_job_step(job_id, "psd", "Building semantic document", 35)
        psd = build_psd(extracted, provider=provider)
        psd_path = output_dir / "psd.json"
        save_json(psd_path, psd)

        _set_job_step(job_id, "story_plan", "Planning the story", 55)
        story_plan = build_story_plan(psd, provider=provider)
        story_plan_path = output_dir / "story_plan.json"
        save_json(story_plan_path, story_plan)

        _set_job_step(job_id, "storyboard", "Writing storyboard", 75)
        storyboard = build_storyboard(psd, story_plan, provider=provider)
        storyboard_path = output_dir / "storyboard.json"
        save_json(storyboard_path, storyboard)

        _set_job_step(job_id, "prompts", "Generating video prompts", 92)
        video_prompts = build_video_prompts(storyboard, provider=provider)
        video_prompts_json_path = output_dir / "video_prompts.json"
        video_prompts_md_path = output_dir / "video_prompts.md"
        save_json(video_prompts_json_path, video_prompts)
        save_video_prompts_markdown(video_prompts_md_path, video_prompts)

        result = _load_run(output_dir.name)
        result["generated_files"] = [
            str(extracted_path),
            str(psd_path),
            str(story_plan_path),
            str(storyboard_path),
            str(video_prompts_json_path),
            str(video_prompts_md_path),
        ]
        _set_job(
            job_id,
            status="done",
            step="done",
            message="Done",
            progress=100,
            result=result,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="error",
            message=str(exc),
            error=str(exc),
        )


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    job = _job_snapshot(job_id)
    if not job:
        return _json_response({"error": "Job not found"}, 404)
    return _json_response(job)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/runs")
def list_runs():
    ensure_dir(OUTPUT_DIR)
    runs = []
    for path in sorted(OUTPUT_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_dir():
            continue
        if not any((path / name).exists() for name in ALLOWED_DOWNLOADS):
            continue
        try:
            runs.append(_run_summary(path.name))
        except Exception:
            runs.append({"run_id": path.name, "path": str(path), "slide_count": 0, "segments": 0, "scenes": 0, "prompts": 0, "files": []})
    return _json_response({"runs": runs})


@app.get("/api/runs/<run_id>")
def get_run(run_id: str):
    try:
        return _json_response(_load_run(run_id))
    except FileNotFoundError:
        return _json_response({"error": "Run not found"}, 404)
    except Exception as exc:
        return _json_response({"error": str(exc)}, 400)


@app.post("/api/run")
def create_run():
    upload = request.files.get("ppt")
    if upload is None or not upload.filename:
        return _json_response({"error": "Please upload a PPTX file"}, 400)
    if not upload.filename.lower().endswith(".pptx"):
        return _json_response({"error": "Only .pptx files are supported"}, 400)

    provider = request.form.get("provider", config.LLM_PROVIDER).strip().lower()
    if provider not in {"mock", "openai"}:
        return _json_response({"error": "Provider must be mock or openai"}, 400)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(upload.filename)
    run_name = request.form.get("run_name", "").strip()
    if not run_name:
        run_name = f"{Path(filename).stem}_{provider}_{timestamp}"
    run_id = _safe_run_id(run_name)

    ensure_dir(INPUT_UPLOAD_DIR)
    ensure_dir(OUTPUT_DIR)
    pptx_path = INPUT_UPLOAD_DIR / f"{timestamp}_{filename}"
    upload.save(pptx_path)

    output_dir = _run_dir(run_id)
    ensure_dir(output_dir)

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "run_id": output_dir.name,
            "status": "queued",
            "step": "queued",
            "message": "Queued",
            "progress": 2,
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": None,
        }

    worker = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id, pptx_path, output_dir, provider),
        daemon=True,
    )
    worker.start()
    return _json_response(_job_snapshot(job_id), 202)


@app.post("/api/runs/<run_id>/story-plan")
def update_story_plan(run_id: str):
    body = request.get_json(silent=True) or {}
    provider = (request.args.get("provider") or body.get("provider") or config.LLM_PROVIDER).strip().lower()
    if provider not in {"mock", "openai"}:
        return _json_response({"error": "Provider must be mock or openai"}, 400)

    data = body.get("story_plan")
    if data is None:
        return _json_response({"error": "Missing story_plan JSON"}, 400)

    run_dir = _run_dir(run_id)
    psd_path = run_dir / "psd.json"
    if not psd_path.exists():
        return _json_response({"error": "psd.json is required before rebuilding"}, 400)

    try:
        psd = PresentationSemanticDocument.model_validate(load_json(psd_path))
        story_plan = StoryPlanDocument.model_validate(data)
        save_json(run_dir / "story_plan.json", story_plan)
        storyboard = build_storyboard(psd, story_plan, provider=provider)
        save_json(run_dir / "storyboard.json", storyboard)
        video_prompts = build_video_prompts(storyboard, provider=provider)
        save_json(run_dir / "video_prompts.json", video_prompts)
        save_video_prompts_markdown(run_dir / "video_prompts.md", video_prompts)
        return _json_response(_load_run(run_id))
    except Exception as exc:
        return _json_response({"error": str(exc)}, 400)


@app.get("/api/runs/<run_id>/download/<filename>")
def download_file(run_id: str, filename: str):
    if filename not in ALLOWED_DOWNLOADS:
        return _json_response({"error": "File not available for download"}, 404)
    path = _run_dir(run_id) / filename
    if not path.exists():
        return _json_response({"error": "File not found"}, 404)
    return send_file(path, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "7860"))
    debug = os.getenv("WEB_DEBUG", "false").strip().lower() in {"1", "true", "yes", "y"}
    app.run(host=host, port=port, debug=debug)
