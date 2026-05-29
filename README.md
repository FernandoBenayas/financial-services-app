# Financial Services AI Workbench

A Python web application that implements all 52 financial services skills from the [anthropics/financial-services](https://github.com/anthropics/financial-services) repository, with dual LLM support (Anthropic Claude & Mistral AI).

## Features

- **52 Professional Skills** across 7 financial verticals:
  - Financial Analysis (13 skills) — comps, DCF, LBO, 3-statement, Excel audit, etc.
  - Investment Banking (9 skills) — CIMs, teasers, merger models, pitch decks, etc.
  - Equity Research (9 skills) — earnings analysis, initiating coverage, sector overviews, etc.
  - Private Equity (10 skills) — deal sourcing, IC memos, returns analysis, etc.
  - Wealth Management (6 skills) — financial plans, rebalancing, TLH, etc.
  - Fund Administration (6 skills) — GL reconciliation, accruals, NAV tie-out, etc.
  - Operations (2 skills) — KYC document parsing and rules evaluation

- **Dual LLM Support** — Switch between Anthropic Claude and Mistral AI models
- **Streaming Responses** — Real-time output with Server-Sent Events
- **File Upload** — Attach documents for skills that process files (KYC, GL data, etc.)
- **Responsive UI** — Clean Bootstrap 5 interface organized by financial vertical
- **Markdown Rendering** — Professional output with tables, code blocks, and formatting

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/FernandoBenayas/financial-services-app.git
cd financial-services-app

# Clone the skills repo (required for skill definitions)
git clone https://github.com/anthropics/financial-services.git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   MISTRAL_API_KEY=...
```

### 3. Run

```bash
python run.py
```

Visit [http://localhost:5000](http://localhost:5000)

### Production

```bash
gunicorn "app.main:create_app()" --bind 0.0.0.0:8000 --workers 4
```

## Architecture

```
financial-services-app/
├── app/
│   ├── __init__.py
│   ├── main.py            # Flask app, routes, SSE streaming
│   ├── llm.py             # LLM connectors (Anthropic + Mistral)
│   ├── skills.py          # Skills registry, loads SKILL.md files
│   ├── static/
│   │   ├── css/style.css  # Custom styles
│   │   └── js/app.js      # Client-side streaming & UI logic
│   └── templates/
│       ├── base.html      # Layout with nav, settings modal
│       ├── index.html     # Dashboard with vertical cards
│       ├── vertical.html  # Skills listing per vertical
│       ├── skill.html     # Individual skill page with chat
│       └── 404.html
├── run.py                 # Dev entry point
├── requirements.txt
├── .env.example
└── README.md
```

## How It Works

1. **Skills Registry** (`app/skills.py`) scans the `financial-services/plugins/vertical-plugins/` directory and loads every `SKILL.md` file with its frontmatter metadata.

2. **LLM Connectors** (`app/llm.py`) provide a unified interface to both Anthropic and Mistral APIs with streaming support.

3. **Flask App** (`app/main.py`) serves the web UI and exposes an `/api/chat` SSE endpoint that:
   - Takes a skill ID, user message, provider, and model
   - Builds a system prompt from the skill's full SKILL.md content
   - Streams the LLM response back to the browser

4. **Client JS** (`app/static/js/app.js`) handles streaming, markdown rendering, provider switching, and file upload.

## Supported Models

### Anthropic
- Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- Claude Haiku 4 (`claude-haiku-4-20250414`)

### Mistral
- Mistral Large (`mistral-large-latest`)
- Mistral Small (`mistral-small-latest`)
- Mistral Nemo (`open-mistral-nemo`)

## License

Apache License 2.0 — Skills content from [anthropics/financial-services](https://github.com/anthropics/financial-services).
