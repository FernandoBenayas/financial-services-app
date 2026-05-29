"""Skills registry — structured skill definitions with input fields and data requirements."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class FormField:
    name: str
    label: str
    field_type: str  # text, textarea, select, number, ticker, tickers, file
    placeholder: str = ""
    required: bool = True
    options: list[str] | None = None
    help_text: str = ""


@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    vertical: str
    command: str | None
    fields: list[FormField]
    data_needs: list[str]  # company_data, financials, news, web_search, peers, earnings
    raw_prompt: str
    file_path: str

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()

    @property
    def vertical_display(self) -> str:
        return self.vertical.replace("-", " ").title()


VERTICAL_META: dict[str, dict[str, str]] = {
    "financial-analysis": {
        "label": "Financial Analysis",
        "icon": "chart-line",
        "color": "#1a5276",
        "description": "Core modeling, Excel audit, deck QC, and data connectors.",
    },
    "investment-banking": {
        "label": "Investment Banking",
        "icon": "landmark",
        "color": "#7d3c98",
        "description": "Deal materials, execution docs, CIMs, teasers, and M&A models.",
    },
    "equity-research": {
        "label": "Equity Research",
        "icon": "magnifying-glass-chart",
        "color": "#1e8449",
        "description": "Coverage, publishing, earnings analysis, and sector reports.",
    },
    "private-equity": {
        "label": "Private Equity",
        "icon": "handshake",
        "color": "#b9770e",
        "description": "Sourcing, screening, diligence, IC memos, and portfolio ops.",
    },
    "wealth-management": {
        "label": "Wealth Management",
        "icon": "piggy-bank",
        "color": "#2e86c1",
        "description": "Client reviews, financial plans, rebalancing, and TLH.",
    },
    "fund-admin": {
        "label": "Fund Administration",
        "icon": "file-invoice-dollar",
        "color": "#cb4335",
        "description": "GL recon, break tracing, accruals, roll-forwards, and NAV tie-out.",
    },
    "operations": {
        "label": "Operations & Onboarding",
        "icon": "clipboard-check",
        "color": "#5b2c6f",
        "description": "KYC document parsing and rules-grid evaluation.",
    },
}

# ── Form field templates ──

_TICKER = FormField("ticker", "Company Ticker", "ticker", "e.g. AAPL, MSFT, TSLA")
_COMPANY = FormField("company_name", "Company Name", "text", "e.g. Apple Inc.")
_QUARTER = FormField("quarter", "Quarter", "select", options=["Q1", "Q2", "Q3", "Q4"])
_YEAR = FormField("year", "Year", "number", "e.g. 2025")
_SECTOR = FormField("sector", "Sector / Industry", "text", "e.g. Cloud Infrastructure, U.S. Regional Banks")
_PEERS = FormField("peer_tickers", "Peer Tickers (comma-separated)", "tickers",
                    "e.g. MSFT, GOOG, AMZN, META", required=False)
_ADDITIONAL = FormField("additional_context", "Additional Context", "textarea",
                        "Any extra details, constraints, or focus areas…", required=False)
_FILE = FormField("file_upload", "Upload Document (optional)", "file", required=False,
                  help_text="Upload CSV, Excel, text, or PDF files with relevant data")


def _build_skill_defs() -> dict[str, dict]:
    """Define structured metadata for every skill."""
    return {
        # ── Financial Analysis ──
        "comps-analysis": {
            "fields": [_TICKER, _COMPANY, _PEERS,
                       FormField("focus", "Analysis Focus", "select",
                                 options=["Valuation", "Growth Analysis", "Competitive Positioning", "M&A Evaluation"]),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "peers", "web_search"],
        },
        "dcf-model": {
            "fields": [_TICKER, _COMPANY,
                       FormField("projection_years", "Projection Years", "number", "5"),
                       FormField("wacc_estimate", "WACC Estimate (%)", "number", "e.g. 9.5", required=False),
                       FormField("terminal_growth", "Terminal Growth Rate (%)", "number", "e.g. 3.0", required=False),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "web_search"],
        },
        "lbo-model": {
            "fields": [_TICKER, _COMPANY,
                       FormField("entry_ebitda", "Entry EBITDA ($M)", "number", "e.g. 500"),
                       FormField("entry_multiple", "Entry Multiple (EV/EBITDA)", "number", "e.g. 8.0"),
                       FormField("leverage", "Total Leverage (x EBITDA)", "number", "e.g. 5.0"),
                       FormField("hold_period", "Hold Period (years)", "number", "e.g. 5"),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials"],
        },
        "3-statement-model": {
            "fields": [_TICKER, _COMPANY,
                       FormField("projection_years", "Projection Years", "number", "3-5"),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials"],
        },
        "audit-xls": {
            "fields": [FormField("model_description", "Model Description", "textarea",
                                 "Describe the Excel model to audit (structure, key formulas, concerns)"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "clean-data-xls": {
            "fields": [FormField("data_description", "Data Description", "textarea",
                                 "Describe the data and cleaning needed (columns, issues, target format)"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "deck-refresh": {
            "fields": [FormField("deck_description", "Deck Description", "textarea",
                                 "Describe the deck and what charts/tables need refreshing"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "competitive-analysis": {
            "fields": [_SECTOR,
                       FormField("companies", "Key Companies to Analyze", "text",
                                 "e.g. AWS, Azure, GCP or leave blank for auto-discovery", required=False),
                       FormField("focus", "Focus Area", "select",
                                 options=["Market Positioning", "Growth Comparison",
                                          "Technology Differentiation", "Pricing Analysis"]),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "ib-check-deck": {
            "fields": [FormField("deck_content", "Deck Content / Outline", "textarea",
                                 "Paste the deck outline or describe its contents for QC"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "pptx-author": {
            "fields": [FormField("deck_brief", "Deck Brief", "textarea",
                                 "Describe the PowerPoint: audience, topic, number of slides, key messages"),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "xlsx-author": {
            "fields": [FormField("workbook_brief", "Workbook Brief", "textarea",
                                 "Describe the Excel workbook: sheets, data, calculations, purpose"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "ppt-template-creator": {
            "fields": [FormField("brand_info", "Brand / Style Info", "textarea",
                                 "Colors, fonts, layout preferences, company branding guidelines"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "skill-creator": {
            "fields": [FormField("skill_description", "New Skill Description", "textarea",
                                 "Describe the skill: domain, workflow steps, inputs, outputs"),
                       _ADDITIONAL],
            "data_needs": [],
        },

        # ── Investment Banking ──
        "strip-profile": {
            "fields": [_TICKER, _COMPANY, _SECTOR, _ADDITIONAL],
            "data_needs": ["company_data", "financials", "news"],
        },
        "pitch-deck": {
            "fields": [_TICKER, _COMPANY,
                       FormField("deal_type", "Deal Type", "select",
                                 options=["M&A Sell-side", "M&A Buy-side", "IPO", "Debt Financing",
                                          "Equity Offering", "Strategic Advisory"]),
                       FormField("key_points", "Key Points to Cover", "textarea",
                                 "Specific data points, themes, or messages for the deck"),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "web_search"],
        },
        "datapack-builder": {
            "fields": [_TICKER, _COMPANY,
                       FormField("focus_areas", "Focus Areas", "textarea",
                                 "Key areas to cover in the data pack (financials, operations, market)"),
                       _FILE, _ADDITIONAL],
            "data_needs": ["company_data", "financials", "news"],
        },
        "cim-builder": {
            "fields": [_COMPANY,
                       FormField("industry", "Industry", "text", "e.g. Healthcare IT, Industrial Services"),
                       FormField("revenue", "Annual Revenue ($M)", "number", "e.g. 150"),
                       FormField("ebitda", "EBITDA ($M)", "number", "e.g. 30"),
                       FormField("business_description", "Business Description", "textarea",
                                 "Products/services, customer base, competitive advantages"),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "teaser": {
            "fields": [FormField("industry", "Industry", "text", "e.g. Enterprise SaaS"),
                       FormField("revenue_range", "Revenue Range", "text", "e.g. $50-100M"),
                       FormField("key_metrics", "Key Metrics", "textarea",
                                 "Growth rate, margins, customer count, etc."),
                       FormField("highlights", "Investment Highlights", "textarea",
                                 "3-5 key selling points"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "buyer-list": {
            "fields": [_COMPANY, _SECTOR,
                       FormField("company_size", "Target Company Size", "text", "e.g. $50M ARR, $200M revenue"),
                       FormField("buyer_type", "Buyer Type Focus", "select",
                                 options=["Strategic + Financial", "Strategic Only", "Financial Only"]),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "merger-model": {
            "fields": [
                FormField("acquirer_ticker", "Acquirer Ticker", "ticker", "e.g. MSFT"),
                FormField("target_ticker", "Target Ticker", "ticker", "e.g. ATVI"),
                FormField("offer_premium", "Offer Premium (%)", "number", "e.g. 25"),
                FormField("cash_pct", "Cash Consideration (%)", "number", "e.g. 50"),
                FormField("synergies", "Expected Synergies ($M)", "number", "e.g. 500", required=False),
                _ADDITIONAL],
            "data_needs": ["company_data", "financials", "peers"],
        },
        "process-letter": {
            "fields": [FormField("transaction_type", "Transaction Type", "select",
                                 options=["Sell-side Auction", "Buy-side Bid", "Recapitalization",
                                          "Minority Investment"]),
                       FormField("transaction_details", "Transaction Details", "textarea",
                                 "Key terms, timeline, bidding process details"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "deal-tracker": {
            "fields": [FormField("deals", "Active Deals", "textarea",
                                 "List active deals with status (e.g. 'Project Alpha - LOI signed, "
                                 "due diligence phase')"),
                       _ADDITIONAL],
            "data_needs": [],
        },

        # ── Equity Research ──
        "earnings-analysis": {
            "fields": [_TICKER, _COMPANY, _QUARTER, _YEAR, _ADDITIONAL],
            "data_needs": ["company_data", "financials", "earnings", "news"],
        },
        "earnings-preview": {
            "fields": [_TICKER, _COMPANY, _QUARTER, _YEAR, _ADDITIONAL],
            "data_needs": ["company_data", "financials", "earnings", "news", "web_search"],
        },
        "initiating-coverage": {
            "fields": [_TICKER, _COMPANY,
                       FormField("task", "Task to Execute", "select",
                                 options=["1 - Company Research", "2 - Financial Modeling",
                                          "3 - Valuation Analysis", "4 - Chart Generation",
                                          "5 - Report Assembly"]),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "news", "web_search"],
        },
        "model-update": {
            "fields": [_TICKER, _COMPANY,
                       FormField("update_trigger", "Update Trigger", "select",
                                 options=["Earnings Release", "Guidance Change", "Estimate Revision",
                                          "Macro Update", "Event-Driven"]),
                       FormField("new_data", "New Data Points", "textarea",
                                 "Key new numbers to incorporate (revenue, EPS, guidance, etc.)"),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "earnings", "news"],
        },
        "morning-note": {
            "fields": [_SECTOR,
                       FormField("coverage_tickers", "Coverage Universe Tickers", "tickers",
                                 "e.g. AAPL, MSFT, GOOG, AMZN", required=False),
                       FormField("analyst_name", "Analyst Name", "text", "Your name", required=False),
                       _ADDITIONAL],
            "data_needs": ["news", "web_search"],
        },
        "sector-overview": {
            "fields": [_SECTOR,
                       FormField("depth", "Report Depth", "select",
                                 options=["High-level overview (5-10 pages)",
                                          "Deep dive (20-30 pages)"]),
                       FormField("angle", "Angle", "select",
                                 options=["Neutral landscape", "Thematic thesis",
                                          "M&A target identification", "Competitive positioning"]),
                       FormField("key_companies", "Key Companies to Include", "tickers",
                                 "Tickers or names (leave blank for auto-discovery)", required=False),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news", "peers"],
        },
        "thesis-tracker": {
            "fields": [_TICKER, _COMPANY,
                       FormField("position", "Position", "select", options=["Long", "Short", "Watchlist"]),
                       FormField("thesis_statement", "Thesis Statement", "textarea",
                                 "1-2 sentence core thesis"),
                       FormField("key_pillars", "Key Pillars (one per line)", "textarea",
                                 "3-5 supporting arguments"),
                       FormField("key_risks", "Key Risks (one per line)", "textarea",
                                 "3-5 risks that would invalidate the thesis"),
                       _ADDITIONAL],
            "data_needs": ["company_data", "news"],
        },
        "catalyst-calendar": {
            "fields": [FormField("coverage_tickers", "Coverage Universe Tickers", "tickers",
                                 "e.g. AAPL, MSFT, GOOG, NVDA"),
                       FormField("time_horizon", "Time Horizon", "select",
                                 options=["Next 2 weeks", "Next month", "Next quarter"]),
                       FormField("include_macro", "Include Macro Events?", "select",
                                 options=["Yes", "No"]),
                       _ADDITIONAL],
            "data_needs": ["news", "web_search", "earnings"],
        },
        "idea-generation": {
            "fields": [FormField("direction", "Direction", "select",
                                 options=["Long ideas", "Short ideas", "Both"]),
                       FormField("market_cap", "Market Cap", "select",
                                 options=["Large-cap", "Mid-cap", "Small-cap", "Micro-cap", "Any"]),
                       _SECTOR,
                       FormField("style", "Investment Style", "select",
                                 options=["Value", "Growth", "Quality", "Special Situation",
                                          "Event-Driven", "Thematic"]),
                       FormField("theme", "Thematic Angle (if any)", "text",
                                 "e.g. AI infrastructure, reshoring, aging demographics", required=False),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },

        # ── Private Equity ──
        "deal-sourcing": {
            "fields": [_SECTOR,
                       FormField("revenue_range", "Target Revenue Range", "text", "e.g. $10-50M"),
                       FormField("ebitda_range", "Target EBITDA Range", "text", "e.g. $3-15M", required=False),
                       FormField("geography", "Geography", "text", "e.g. US, Southeast, Texas"),
                       FormField("ownership_type", "Ownership Type", "select",
                                 options=["Any", "Founder-owned", "PE-backed", "Corporate carve-out"]),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "deal-screening": {
            "fields": [_COMPANY,
                       FormField("deal_overview", "Deal Overview / CIM Summary", "textarea",
                                 "Key metrics: revenue, EBITDA, growth, margins, asking price"),
                       _FILE, _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "dd-checklist": {
            "fields": [_COMPANY,
                       FormField("deal_stage", "Deal Stage", "select",
                                 options=["Preliminary", "Confirmatory", "Final"]),
                       FormField("workstreams", "Workstreams to Cover", "select",
                                 options=["All", "Commercial", "Financial", "Legal",
                                          "Operational", "IT/Technology", "HR/Management"]),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "dd-meeting-prep": {
            "fields": [_COMPANY,
                       FormField("meeting_type", "Meeting Type", "select",
                                 options=["Management Presentation", "Expert Call",
                                          "Customer Reference Call", "Site Visit"]),
                       FormField("key_concerns", "Key Concerns / Focus Areas", "textarea",
                                 "What do you most want to learn in this meeting?"),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "unit-economics": {
            "fields": [_TICKER, _COMPANY,
                       FormField("business_model", "Business Model", "select",
                                 options=["SaaS", "Marketplace", "E-commerce",
                                          "Subscription (non-SaaS)", "Services", "Other"]),
                       FormField("metrics", "Known Metrics (paste any you have)", "textarea",
                                 "ARR, churn, LTV, CAC, net retention, etc.", required=False),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "web_search"],
        },
        "returns-analysis": {
            "fields": [
                FormField("entry_ebitda", "Entry EBITDA ($M)", "number", "e.g. 50"),
                FormField("entry_multiple", "Entry Multiple (EV/EBITDA)", "number", "e.g. 8.0"),
                FormField("leverage", "Total Leverage (x EBITDA)", "number", "e.g. 5.0"),
                FormField("revenue_growth", "Revenue Growth Rate (%)", "number", "e.g. 10"),
                FormField("exit_multiple", "Exit Multiple (EV/EBITDA)", "number", "e.g. 9.0"),
                FormField("hold_period", "Hold Period (years)", "number", "e.g. 5"),
                _ADDITIONAL],
            "data_needs": [],
        },
        "ic-memo": {
            "fields": [_COMPANY,
                       FormField("deal_overview", "Deal Overview", "textarea",
                                 "Company description, deal rationale, key terms, returns"),
                       FormField("deal_price", "Deal Price / Valuation", "text",
                                 "e.g. $500M EV, 8x EBITDA"),
                       _FILE, _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "portfolio-monitoring": {
            "fields": [_TICKER, _COMPANY,
                       FormField("kpis", "KPIs to Track", "textarea",
                                 "Key metrics (revenue, EBITDA margin, customer count, churn, etc.)"),
                       FormField("budget_targets", "Budget / Plan Targets (if any)", "textarea",
                                 "Expected vs. actual performance", required=False),
                       _ADDITIONAL],
            "data_needs": ["company_data", "financials", "news"],
        },
        "value-creation-plan": {
            "fields": [_COMPANY,
                       FormField("deal_context", "Deal Context", "textarea",
                                 "Company overview, entry thesis, key value levers"),
                       FormField("entry_ebitda", "Entry EBITDA ($M)", "number", "e.g. 30"),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "ai-readiness": {
            "fields": [_COMPANY,
                       FormField("industry", "Industry", "text", "e.g. Healthcare SaaS"),
                       FormField("company_overview", "Company Overview", "textarea",
                                 "Business model, products, tech stack, team size"),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },

        # ── Wealth Management ──
        "client-review": {
            "fields": [FormField("client_name", "Client Name", "text", "e.g. Smith Family Trust"),
                       FormField("portfolio_value", "Portfolio Value ($)", "text", "e.g. $2.5M"),
                       FormField("allocation", "Current Allocation", "textarea",
                                 "e.g. 60% equity, 30% fixed income, 10% alternatives"),
                       FormField("meeting_context", "Meeting Context", "select",
                                 options=["Annual Review", "Quarterly Check-in",
                                          "Life Event Discussion", "Market Volatility"]),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "financial-plan": {
            "fields": [FormField("client_age", "Client Age", "number", "e.g. 45"),
                       FormField("spouse_age", "Spouse Age (if applicable)", "number", required=False),
                       FormField("annual_income", "Annual Income ($)", "text", "e.g. $250,000"),
                       FormField("current_savings", "Current Savings / Investments ($)", "text",
                                 "e.g. $1.2M"),
                       FormField("retirement_age", "Target Retirement Age", "number", "e.g. 65"),
                       FormField("annual_expenses", "Annual Expenses ($)", "text", "e.g. $120,000"),
                       FormField("goals", "Financial Goals", "textarea",
                                 "Retirement, education funding, estate planning, etc."),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "portfolio-rebalance": {
            "fields": [FormField("current_allocation", "Current Allocation", "textarea",
                                 "e.g. US Large Cap: 45%, US Small Cap: 10%, Intl: 15%, "
                                 "Fixed Income: 25%, Cash: 5%"),
                       FormField("target_allocation", "Target Allocation", "textarea",
                                 "e.g. US Large Cap: 40%, US Small Cap: 10%, Intl: 20%, "
                                 "Fixed Income: 25%, Cash: 5%"),
                       FormField("portfolio_value", "Portfolio Value ($)", "text", "e.g. $1.5M"),
                       FormField("tax_sensitivity", "Tax Sensitivity", "select",
                                 options=["Tax-aware (taxable account)",
                                          "Tax-neutral (IRA/401k)", "Mixed"]),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "client-report": {
            "fields": [FormField("client_name", "Client Name", "text", "e.g. Johnson Family"),
                       FormField("period", "Reporting Period", "text", "e.g. Q1 2025"),
                       FormField("portfolio_value", "Portfolio Value ($)", "text", "e.g. $3.2M"),
                       FormField("performance", "Performance Summary", "textarea",
                                 "Returns by asset class, benchmark comparison, etc.", required=False),
                       _ADDITIONAL],
            "data_needs": ["web_search", "news"],
        },
        "investment-proposal": {
            "fields": [FormField("prospect_name", "Prospect Name", "text"),
                       FormField("investable_assets", "Investable Assets ($)", "text", "e.g. $5M"),
                       FormField("risk_tolerance", "Risk Tolerance", "select",
                                 options=["Conservative", "Moderate", "Aggressive"]),
                       FormField("investment_goals", "Investment Goals", "textarea",
                                 "Growth, income, capital preservation, estate planning, etc."),
                       FormField("time_horizon", "Time Horizon", "select",
                                 options=["Short-term (1-3 years)", "Medium-term (3-10 years)",
                                          "Long-term (10+ years)"]),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
        "tax-loss-harvesting": {
            "fields": [FormField("positions", "Current Positions", "textarea",
                                 "List positions with cost basis and current value\n"
                                 "e.g. AAPL: 100 shares @ $150, now $170\nTSLA: 50 shares @ $300, now $240"),
                       FormField("tax_rate", "Marginal Tax Rate (%)", "number", "e.g. 37"),
                       FormField("account_type", "Account Type", "select",
                                 options=["Taxable Brokerage", "Trust", "Corporate"]),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },

        # ── Fund Admin ──
        "gl-recon": {
            "fields": [FormField("entity", "Fund / Entity Name", "text", "e.g. Fund III, LP"),
                       FormField("period", "Recon Period", "text", "e.g. 2025-03-31"),
                       FormField("asset_class", "Asset Class", "select",
                                 options=["Equities", "Fixed Income", "Derivatives",
                                          "Real Estate", "Multi-Asset", "Other"]),
                       FormField("gl_data", "GL Extract (paste or describe)", "textarea",
                                 "Key GL balances or paste data"),
                       FormField("subledger_data", "Subledger Extract (paste or describe)",
                                 "textarea", "Key subledger balances or paste data"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "break-trace": {
            "fields": [FormField("break_description", "Break Description", "textarea",
                                 "Describe the reconciliation break: amounts, accounts, dates"),
                       FormField("break_amount", "Break Amount ($)", "text", "e.g. $15,432.50"),
                       FormField("break_type", "Break Type", "select",
                                 options=["Amount break", "Quantity break", "Timing break",
                                          "GL only", "Subledger only", "Unknown"]),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "accrual-schedule": {
            "fields": [FormField("entity", "Fund / Entity Name", "text"),
                       FormField("period_end", "Period End Date", "text", "e.g. 2025-03-31"),
                       FormField("accrual_types", "Accrual Types", "textarea",
                                 "e.g. Management fees, Performance fees, Fund expenses, "
                                 "Interest income"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "roll-forward": {
            "fields": [FormField("account", "Account Name", "text",
                                 "e.g. Investments, Accrued Expenses, Deferred Revenue"),
                       FormField("beginning_balance", "Beginning Balance ($)", "text", "e.g. $1,250,000"),
                       FormField("period", "Period", "text", "e.g. March 2025"),
                       FormField("activity_description", "Activity Description", "textarea",
                                 "Key transactions and activity during the period"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "variance-commentary": {
            "fields": [FormField("entity", "Fund / Entity Name", "text"),
                       FormField("period", "Current Period", "text", "e.g. March 2025"),
                       FormField("comparison", "Comparison", "select",
                                 options=["Current vs Prior Period", "Current vs Budget",
                                          "Current vs Prior Year"]),
                       FormField("line_items", "P&L / BS Lines to Comment On", "textarea",
                                 "Revenue, COGS, OpEx, or paste actual vs comparison figures"),
                       FormField("threshold", "Variance Threshold (%)", "number", "e.g. 10"),
                       _ADDITIONAL],
            "data_needs": [],
        },
        "nav-tieout": {
            "fields": [FormField("fund_name", "Fund Name", "text"),
                       FormField("lp_name", "LP Name", "text"),
                       FormField("nav_data", "NAV Pack Summary (paste or describe)", "textarea",
                                 "Total NAV, component balances, allocation percentages"),
                       FormField("lp_statement_data", "LP Statement Data (paste or describe)",
                                 "textarea", "LP capital account, allocations, distributions"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },

        # ── Operations ──
        "kyc-doc-parse": {
            "fields": [FormField("applicant_type", "Applicant Type", "select",
                                 options=["Individual", "Entity", "Trust"]),
                       FormField("documents_description", "Documents Received", "textarea",
                                 "List documents in the packet (passport, articles of incorporation, etc.)"),
                       _FILE, _ADDITIONAL],
            "data_needs": [],
        },
        "kyc-rules": {
            "fields": [FormField("parsed_record", "Parsed KYC Record (from kyc-doc-parse)", "textarea",
                                 "Paste the structured JSON output from the document parsing step"),
                       FormField("jurisdiction", "Jurisdiction", "text", "e.g. US, UK, Cayman Islands"),
                       _ADDITIONAL],
            "data_needs": ["web_search"],
        },
    }


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a SKILL.md file."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm = content[3:end].strip()
    body = content[end + 3:].strip()
    meta: dict[str, str] = {}
    key = ""
    val_lines: list[str] = []
    for line in fm.split("\n"):
        m = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if m:
            if key:
                meta[key] = "\n".join(val_lines).strip()
            key = m.group(1)
            val_lines = [m.group(2).strip()]
        else:
            val_lines.append(line)
    if key:
        meta[key] = "\n".join(val_lines).strip()
    return meta, body


def load_skills(skills_root: str) -> dict[str, Skill]:
    """Load all SKILL.md files and merge with structured definitions."""
    registry: dict[str, Skill] = {}
    defs = _build_skill_defs()
    verticals_dir = os.path.join(skills_root, "plugins", "vertical-plugins")
    if not os.path.isdir(verticals_dir):
        return registry
    for vertical in sorted(os.listdir(verticals_dir)):
        skills_dir = os.path.join(verticals_dir, vertical, "skills")
        if not os.path.isdir(skills_dir):
            continue
        for slug in sorted(os.listdir(skills_dir)):
            skill_file = os.path.join(skills_dir, slug, "SKILL.md")
            if not os.path.isfile(skill_file):
                continue
            with open(skill_file, encoding="utf-8") as f:
                content = f.read()
            meta, body = _parse_frontmatter(content)
            name = meta.get("name", slug)
            description = meta.get("description", "").strip("|").strip()
            skill_def = defs.get(slug, {})
            skill = Skill(
                skill_id=slug,
                name=name,
                description=description,
                vertical=vertical,
                command=None,
                fields=skill_def.get("fields", [
                    FormField("request", "Your Request", "textarea",
                              "Describe what you need…"),
                    _ADDITIONAL,
                ]),
                data_needs=skill_def.get("data_needs", []),
                raw_prompt=content,
                file_path=skill_file,
            )
            registry[slug] = skill
    return registry


def get_skills_by_vertical(registry: dict[str, Skill]) -> dict[str, list[Skill]]:
    grouped: dict[str, list[Skill]] = {}
    for skill in registry.values():
        grouped.setdefault(skill.vertical, []).append(skill)
    return grouped
