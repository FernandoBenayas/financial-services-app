"""Flask application — Financial Services AI Workbench."""

from __future__ import annotations

import json
import os

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

from .llm import ALL_MODELS, stream
from .skills import (
    INPUT_HINTS,
    VERTICAL_META,
    Skill,
    get_skills_by_vertical,
    load_skills,
)

SKILLS_REPO_ROOT = os.environ.get(
    "SKILLS_REPO_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "financial-services"),
)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB uploads

    registry = load_skills(SKILLS_REPO_ROOT)
    by_vertical = get_skills_by_vertical(registry)

    @app.context_processor
    def inject_globals() -> dict:
        return {"verticals": VERTICAL_META}

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
            verticals=VERTICAL_META,
            by_vertical=by_vertical,
            total_skills=len(registry),
        )

    @app.route("/vertical/<vertical_id>")
    def vertical_page(vertical_id: str) -> str | tuple[str, int]:
        if vertical_id not in VERTICAL_META:
            return render_template("404.html", message="Vertical not found"), 404
        skills = by_vertical.get(vertical_id, [])
        return render_template(
            "vertical.html",
            vertical_id=vertical_id,
            meta=VERTICAL_META[vertical_id],
            skills=skills,
            input_hints=INPUT_HINTS,
        )

    @app.route("/skill/<skill_id>")
    def skill_page(skill_id: str) -> str | tuple[str, int]:
        skill = registry.get(skill_id)
        if skill is None:
            return render_template("404.html", message="Skill not found"), 404
        return render_template(
            "skill.html",
            skill=skill,
            meta=VERTICAL_META.get(skill.vertical, {}),
            models=ALL_MODELS,
            input_hint=INPUT_HINTS.get(skill_id, "Describe your request…"),
        )

    @app.route("/api/models")
    def api_models() -> Response:
        return jsonify(ALL_MODELS)

    @app.route("/api/skills")
    def api_skills() -> Response:
        out = {}
        for sid, sk in registry.items():
            out[sid] = {
                "name": sk.display_name,
                "vertical": sk.vertical,
                "description": sk.description,
                "command": sk.command,
            }
        return jsonify(out)

    @app.route("/api/chat", methods=["POST"])
    def api_chat() -> Response:
        data = request.get_json(force=True)
        skill_id = data.get("skill_id", "")
        user_message = data.get("message", "")
        provider = data.get("provider", "anthropic")
        model = data.get("model")
        file_content = data.get("file_content", "")

        skill = registry.get(skill_id)
        if skill is None:
            return jsonify({"error": f"Unknown skill: {skill_id}"}), 400
        if not user_message and not file_content:
            return jsonify({"error": "Message is required"}), 400

        system_prompt = _build_system_prompt(skill)
        full_message = user_message
        if file_content:
            full_message += f"\n\n--- Uploaded Document Content ---\n{file_content}"

        def generate():
            try:
                for chunk in stream(
                    system_prompt=system_prompt,
                    user_message=full_message,
                    provider=provider,
                    model=model,
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[str, int]:
        return render_template("404.html", message="Page not found"), 404

    return app


def _build_system_prompt(skill: Skill) -> str:
    """Build the system prompt from the skill's raw markdown."""
    preamble = (
        "You are an expert financial services AI assistant. "
        "You are executing the following skill from the Claude Financial Services toolkit. "
        "Follow the workflow, conventions, and output formats described in the skill precisely. "
        "Produce institutional-quality output suitable for professional review. "
        "Use markdown formatting in your response for readability.\n\n"
    )
    return preamble + skill.raw_prompt
