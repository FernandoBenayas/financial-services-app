# Financial Services AI Workbench

A Python web application that implements 55 professional financial analysis tools powered by real-time market data and dual LLM support (Anthropic Claude & Mistral AI).

Each tool is a real functional feature — enter a company ticker and the app automatically fetches live financials, news, and market data from Yahoo Finance and web search, then runs AI-powered analysis following institutional workflows from the [anthropics/financial-services](https://github.com/anthropics/financial-services) skill library.

## Features

- **55 Functional Tools** across 7 financial verticals:
  - **Equity Research** — earnings analysis, pre-earnings previews, initiating coverage, model updates, morning notes, sector overviews, thesis tracking, catalyst calendars, idea generation
  - **Financial Analysis** — comparable company analysis, DCF models, LBO models, 3-statement models, competitive analysis, Excel audit, data cleaning
  - **Investment Banking** — one-pagers, pitch decks, CIMs, teasers, buyer lists, merger models, process letters, deal tracking
  - **Private Equity** — deal sourcing, screening, DD checklists, unit economics, returns analysis, IC memos, portfolio monitoring, value creation plans
  - **Wealth Management** — client reviews, financial plans, rebalancing, investment proposals, tax-loss harvesting
  - **Fund Administration** — GL reconciliation, break tracing, accruals, roll-forwards, variance commentary, NAV tie-out
  - **Operations** — KYC document parsing and rules evaluation

- **Real-Time Data Fetching** — Yahoo Finance for financials, DuckDuckGo search for news and web research
- **Structured Input Forms** — each tool has dedicated fields (ticker lookup, financial parameters, peer groups, etc.)
- **Dual LLM Support** — switch between Anthropic Claude and Mistral AI models
- **Streaming Responses** — real-time output with live data gathering status
- **Ticker Lookup** — instant company info when you enter a ticker symbol

## Quick Start

### 1. Clone & Setup

```bash
git clone <this-repo>
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
# Edit .env — you need at least one:
#   ANTHROPIC_API_KEY=sk-ant-...
#   MISTRAL_API_KEY=...
```

### 3. Run

```bash
python run.py
```

Visit [http://localhost:5000](http://localhost:5000)

## How It Works

1. **Choose a tool** from the dashboard (organized by financial vertical)
2. **Fill in the structured form** — enter company tickers, financial parameters, or context
3. **Auto-fetch data** — the app queries Yahoo Finance for financials, plus DuckDuckGo for recent news and web research
4. **AI analysis** — all gathered data + the skill's institutional workflow are sent to the LLM, which produces professional-quality output
5. **Streaming results** — output renders in real-time with markdown formatting, tables, and charts

## Architecture

```
app/
├── main.py          # Flask routes, SSE streaming, context building
├── llm.py           # Anthropic + Mistral connectors with streaming
├── skills.py        # Skill registry with structured form definitions
├── data_fetcher.py  # Yahoo Finance + DuckDuckGo data fetching
├── static/          # CSS, JavaScript
└── templates/       # Jinja2 templates (dashboard, vertical, skill pages)
```

## Supported Models

| Provider | Models |
|----------|--------|
| Anthropic | Claude Sonnet 4, Claude Haiku 4 |
| Mistral | Mistral Large, Mistral Small, Mistral Nemo |

## License

Apache License 2.0 — Skill workflows from [anthropics/financial-services](https://github.com/anthropics/financial-services).
