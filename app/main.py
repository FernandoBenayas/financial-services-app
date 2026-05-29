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

from .data_fetcher import (
    fetch_company_data,
    fetch_earnings_history,
    fetch_financials,
    fetch_peer_data,
    format_company_summary,
    format_financials_summary,
    format_news_summary,
    search_news,
    search_web,
)
from .llm import ANTHROPIC_MODELS, MISTRAL_MODELS, stream
from .skills import (
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
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    registry = load_skills(SKILLS_REPO_ROOT)
    by_vertical = get_skills_by_vertical(registry)

    @app.context_processor
    def inject_globals() -> dict:
        return {"verticals": VERTICAL_META}

    # ── Pages ──

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
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
            anthropic_models=ANTHROPIC_MODELS,
            mistral_models=MISTRAL_MODELS,
        )

    # ── API ──

    @app.route("/api/execute", methods=["POST"])
    def api_execute() -> Response:
        data = request.get_json(force=True)
        skill_id = data.get("skill_id", "")
        form_data = data.get("form_data", {})
        provider = data.get("provider", "anthropic")
        model = data.get("model")
        file_content = data.get("file_content", "")

        skill = registry.get(skill_id)
        if skill is None:
            return jsonify({"error": f"Unknown skill: {skill_id}"}), 400

        def generate():
            try:
                # Phase 1: gather context from web
                context_parts: list[str] = []
                tickers: list[str] = []
                ticker = form_data.get("ticker", "").strip().upper()
                if ticker:
                    tickers.append(ticker)

                peer_str = form_data.get("peer_tickers", "") or ""
                peer_tickers = [t.strip().upper() for t in peer_str.split(",") if t.strip()]

                key_companies_str = form_data.get("key_companies", "") or ""
                key_companies = [t.strip().upper() for t in key_companies_str.split(",")
                                 if t.strip()]

                coverage_str = form_data.get("coverage_tickers", "") or ""
                coverage_tickers = [t.strip().upper() for t in coverage_str.split(",")
                                    if t.strip()]

                acquirer_tick = form_data.get("acquirer_ticker", "").strip().upper()
                target_tick = form_data.get("target_ticker", "").strip().upper()

                yield _sse({"status": "Gathering data…"})

                # Company data
                if "company_data" in skill.data_needs and ticker:
                    yield _sse({"status": f"Fetching data for {ticker}…"})
                    cd = fetch_company_data(ticker)
                    if cd:
                        context_parts.append(format_company_summary(cd))

                # Financial statements
                if "financials" in skill.data_needs and ticker:
                    yield _sse({"status": f"Fetching financials for {ticker}…"})
                    fin = fetch_financials(ticker)
                    if fin:
                        context_parts.append(format_financials_summary(fin))

                # Earnings history
                if "earnings" in skill.data_needs and ticker:
                    yield _sse({"status": f"Fetching earnings history for {ticker}…"})
                    eh = fetch_earnings_history(ticker)
                    if eh:
                        context_parts.append("## Earnings History\n" +
                                             json.dumps(eh[:8], indent=2, default=str))

                # Peer comparisons
                if "peers" in skill.data_needs and (peer_tickers or key_companies):
                    all_peers = peer_tickers + key_companies
                    yield _sse({"status": f"Fetching peer data ({', '.join(all_peers[:5])})…"})
                    peers = fetch_peer_data(all_peers)
                    for p in peers:
                        context_parts.append(format_company_summary(p))

                # Merger model: fetch both acquirer + target
                if acquirer_tick and target_tick:
                    for mtick, mlabel in [(acquirer_tick, "Acquirer"),
                                          (target_tick, "Target")]:
                        yield _sse({"status": f"Fetching {mlabel} data ({mtick})…"})
                        mcd = fetch_company_data(mtick)
                        if mcd:
                            context_parts.append(f"### {mlabel}\n" + format_company_summary(mcd))
                        mfin = fetch_financials(mtick)
                        if mfin:
                            context_parts.append(format_financials_summary(mfin))

                # Coverage universe (morning notes, catalyst calendar)
                if coverage_tickers:
                    for ct in coverage_tickers[:10]:
                        yield _sse({"status": f"Fetching data for {ct}…"})
                        ccd = fetch_company_data(ct)
                        if ccd:
                            context_parts.append(format_company_summary(ccd))

                # News
                if "news" in skill.data_needs:
                    search_term = (form_data.get("company_name", "") or
                                   ticker or
                                   form_data.get("sector", "") or
                                   skill.display_name)
                    yield _sse({"status": f"Searching news for {search_term}…"})
                    articles = search_news(f"{search_term} financial news", max_results=6)
                    if articles:
                        context_parts.append(format_news_summary(articles))

                # Web search for additional context
                if "web_search" in skill.data_needs:
                    query_parts = [form_data.get("company_name", ""),
                                   ticker,
                                   form_data.get("sector", ""),
                                   skill.display_name]
                    q = " ".join(p for p in query_parts if p).strip()
                    if q:
                        yield _sse({"status": f"Searching web: {q[:50]}…"})
                        results = search_web(q, max_results=5)
                        if results:
                            web_text = "\n".join(
                                f"- **{r['title']}**: {r['body'][:200]}" for r in results
                            )
                            context_parts.append("## Web Research\n" + web_text)

                # File content
                if file_content:
                    context_parts.append("## Uploaded Document Content\n" + file_content)

                # Phase 2: build the prompt
                yield _sse({"status": "Generating analysis…"})

                system_prompt = _build_system_prompt(skill)
                user_message = _build_user_message(skill, form_data, context_parts)

                # Phase 3: stream LLM response
                for chunk in stream(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    provider=provider,
                    model=model,
                ):
                    yield _sse({"chunk": chunk})
                yield _sse({"done": True})

            except Exception as exc:
                yield _sse({"error": str(exc)})

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/lookup_ticker", methods=["POST"])
    def api_lookup_ticker() -> Response:
        data = request.get_json(force=True)
        ticker = data.get("ticker", "").strip().upper()
        if not ticker:
            return jsonify({"error": "No ticker provided"}), 400
        cd = fetch_company_data(ticker)
        if cd is None:
            return jsonify({"error": f"Could not find data for {ticker}"}), 404
        return jsonify({
            "name": cd.name,
            "sector": cd.sector,
            "industry": cd.industry,
            "price": cd.price,
            "market_cap": cd.market_cap,
        })

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[str, int]:
        return render_template("404.html", message="Page not found"), 404

    return app


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _build_system_prompt(skill: Skill) -> str:
    preamble = (
        "You are an expert financial services AI assistant. "
        "You are executing the following skill from the Claude Financial Services toolkit. "
        "Follow the workflow, conventions, and output formats described below precisely. "
        "Produce institutional-quality output suitable for professional review.\n\n"
        "IMPORTANT: You have been provided with REAL, CURRENT market data and financials "
        "fetched from Yahoo Finance and web search. Use this data as the factual foundation "
        "for your analysis. Do NOT make up numbers — use the data provided. "
        "Where the data is incomplete, clearly note assumptions.\n\n"
        "Format your output in clean markdown with proper headers, tables, and structure.\n\n"
    )
    return preamble + "---\n\n" + skill.raw_prompt


def _build_user_message(
    skill: Skill, form_data: dict, context_parts: list[str]
) -> str:
    """Build a structured user message from form fields and gathered context."""
    parts: list[str] = []

    # Form data section
    parts.append("## Request Parameters\n")
    for field in skill.fields:
        val = form_data.get(field.name, "")
        if val:
            parts.append(f"**{field.label}:** {val}")
    parts.append("")

    # Context section
    if context_parts:
        parts.append("## Real-Time Market Data & Context\n")
        parts.append("The following data has been fetched automatically from "
                     "Yahoo Finance, news sources, and web search:\n")
        parts.extend(context_parts)
        parts.append("")

    # Final instruction
    parts.append("## Task\n")
    parts.append(f"Execute the **{skill.display_name}** workflow using the parameters "
                 "and data above. Produce complete, institutional-quality output "
                 "following the skill's specified format and structure.")

    return "\n\n".join(parts)
