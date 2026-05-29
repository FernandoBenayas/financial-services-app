"""Skills registry — loads and indexes all SKILL.md files from the reference repo."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    vertical: str
    command: str | None
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

COMMAND_MAP: dict[str, str] = {
    "comps-analysis": "/comps",
    "dcf-model": "/dcf",
    "lbo-model": "/lbo",
    "3-statement-model": "/3-statement-model",
    "audit-xls": "/debug-model",
    "competitive-analysis": "/competitive-analysis",
    "ppt-template-creator": "/ppt-template",
    "strip-profile": "/one-pager",
    "cim-builder": "/cim",
    "teaser": "/teaser",
    "buyer-list": "/buyer-list",
    "merger-model": "/merger-model",
    "process-letter": "/process-letter",
    "deal-tracker": "/deal-tracker",
    "earnings-analysis": "/earnings",
    "earnings-preview": "/earnings-preview",
    "initiating-coverage": "/initiate",
    "model-update": "/model-update",
    "morning-note": "/morning-note",
    "sector-overview": "/sector",
    "thesis-tracker": "/thesis",
    "catalyst-calendar": "/catalysts",
    "idea-generation": "/screen",
    "deal-sourcing": "/source",
    "deal-screening": "/screen-deal",
    "dd-checklist": "/dd-checklist",
    "dd-meeting-prep": "/dd-prep",
    "unit-economics": "/unit-economics",
    "returns-analysis": "/returns",
    "ic-memo": "/ic-memo",
    "portfolio-monitoring": "/portfolio",
    "value-creation-plan": "/value-creation",
    "ai-readiness": "/ai-readiness",
    "client-review": "/client-review",
    "financial-plan": "/financial-plan",
    "portfolio-rebalance": "/rebalance",
    "client-report": "/client-report",
    "investment-proposal": "/proposal",
    "tax-loss-harvesting": "/tlh",
}

INPUT_HINTS: dict[str, str] = {
    "comps-analysis": "Enter a company name or ticker and its peer group (e.g., 'Apple Inc. — compare against MSFT, GOOG, AMZN, META')",
    "dcf-model": "Enter a company name/ticker for DCF valuation (e.g., 'Tesla Inc (TSLA) — 5-year projection')",
    "lbo-model": "Enter target company and deal terms (e.g., 'Medline Industries — $34B EV, 7x EBITDA entry')",
    "3-statement-model": "Enter a company name/ticker to build a 3-statement model (e.g., 'Nike Inc (NKE)')",
    "audit-xls": "Describe the Excel model to audit or paste the key formulas/structure you want checked",
    "clean-data-xls": "Describe the data to normalize (columns, issues, target format)",
    "deck-refresh": "Describe the deck and what charts/tables need refreshing",
    "competitive-analysis": "Enter a company or market to analyze (e.g., 'Cloud infrastructure market — AWS vs Azure vs GCP')",
    "ib-check-deck": "Describe the presentation to QC or paste its content outline",
    "pptx-author": "Describe the PowerPoint to generate (audience, content, number of slides)",
    "xlsx-author": "Describe the Excel workbook to generate (sheets, data, purpose)",
    "ppt-template-creator": "Describe the PPT template style (brand colors, fonts, layout preferences)",
    "skill-creator": "Describe the new skill you want to create (domain, workflow, outputs)",
    "strip-profile": "Enter company name for a one-page profile (e.g., 'Stripe — fintech, payments')",
    "pitch-deck": "Describe the pitch deck context (client, deal type, key data points)",
    "datapack-builder": "Describe the data pack to build (source CIM/filings, focus areas)",
    "cim-builder": "Enter company details for the CIM (name, industry, financials overview)",
    "teaser": "Enter company details for the anonymous teaser (industry, size, key metrics)",
    "buyer-list": "Enter target company/asset for buyer universe (e.g., 'SaaS company, $50M ARR, healthcare vertical')",
    "merger-model": "Enter acquirer and target details (e.g., 'Microsoft acquiring Activision — deal terms')",
    "process-letter": "Describe the transaction and process letter needs (bid instructions, timeline)",
    "deal-tracker": "Enter deal name or list of active deals to track",
    "earnings-analysis": "Enter company and quarter (e.g., 'Apple Inc Q1 2025 earnings analysis')",
    "earnings-preview": "Enter company and upcoming quarter (e.g., 'NVIDIA Q4 2025 earnings preview')",
    "initiating-coverage": "Enter company to initiate coverage on (e.g., 'Palantir Technologies — enterprise AI')",
    "model-update": "Enter company and new data to incorporate (e.g., 'MSFT — update with Q3 2025 actuals')",
    "morning-note": "Enter market/sector focus or key overnight developments",
    "sector-overview": "Enter sector/industry to cover (e.g., 'U.S. Regional Banks' or 'AI Infrastructure')",
    "thesis-tracker": "Enter company and current thesis to track/update",
    "catalyst-calendar": "Enter coverage universe or sector for catalyst tracking",
    "idea-generation": "Enter screening criteria (e.g., 'Mid-cap tech, >20% revenue growth, profitable')",
    "deal-sourcing": "Enter target criteria (e.g., 'B2B SaaS, $5-20M ARR, healthcare vertical')",
    "deal-screening": "Describe the inbound deal/CIM to screen (company overview, key metrics)",
    "dd-checklist": "Enter company and deal stage for diligence checklist",
    "dd-meeting-prep": "Enter company and meeting type (e.g., 'Management presentation for Acme Corp')",
    "unit-economics": "Enter company name and key SaaS/business metrics to analyze",
    "returns-analysis": "Enter deal parameters for IRR/MOIC analysis (entry, exit, hold period)",
    "ic-memo": "Enter company and deal overview for IC memo",
    "portfolio-monitoring": "Enter portfolio company name and KPIs to track",
    "value-creation-plan": "Enter portfolio company for post-close 100-day plan",
    "ai-readiness": "Enter portfolio company name to assess AI readiness",
    "client-review": "Enter client name and meeting context (e.g., 'Annual review for the Smith Family Trust')",
    "financial-plan": "Enter client profile (age, income, assets, goals) for financial planning",
    "portfolio-rebalance": "Enter current allocation and target (e.g., '60/40 equity/bond, drifted to 70/30')",
    "client-report": "Enter client name and reporting period",
    "investment-proposal": "Enter prospect details and investment objectives",
    "tax-loss-harvesting": "Enter portfolio details for TLH opportunity analysis",
    "gl-recon": "Describe GL and subledger data to reconcile (entity, period, asset class)",
    "break-trace": "Describe the reconciliation break to root-cause",
    "accrual-schedule": "Enter period-end and accrual types to schedule",
    "roll-forward": "Enter account and period for the roll-forward schedule",
    "variance-commentary": "Enter P&L/BS lines and periods for variance commentary",
    "nav-tieout": "Enter fund and LP details for NAV tie-out",
    "kyc-doc-parse": "Describe or upload the onboarding document packet to parse",
    "kyc-rules": "Enter the parsed KYC record to run through the rules engine",
}


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a SKILL.md file."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    frontmatter_str = content[3:end].strip()
    body = content[end + 3:].strip()
    meta: dict[str, str] = {}
    current_key = ""
    current_val_lines: list[str] = []
    for line in frontmatter_str.split("\n"):
        match = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if match:
            if current_key:
                meta[current_key] = "\n".join(current_val_lines).strip()
            current_key = match.group(1)
            current_val_lines = [match.group(2).strip()]
        else:
            current_val_lines.append(line)
    if current_key:
        meta[current_key] = "\n".join(current_val_lines).strip()
    return meta, body


def load_skills(skills_root: str) -> dict[str, Skill]:
    """Walk the vertical-plugins directory and load every SKILL.md."""
    registry: dict[str, Skill] = {}
    verticals_dir = os.path.join(skills_root, "plugins", "vertical-plugins")
    if not os.path.isdir(verticals_dir):
        return registry
    for vertical in sorted(os.listdir(verticals_dir)):
        skills_dir = os.path.join(verticals_dir, vertical, "skills")
        if not os.path.isdir(skills_dir):
            continue
        for skill_slug in sorted(os.listdir(skills_dir)):
            skill_file = os.path.join(skills_dir, skill_slug, "SKILL.md")
            if not os.path.isfile(skill_file):
                continue
            with open(skill_file, encoding="utf-8") as f:
                content = f.read()
            meta, body = _parse_frontmatter(content)
            name = meta.get("name", skill_slug)
            description = meta.get("description", "").strip("|").strip()
            skill = Skill(
                skill_id=skill_slug,
                name=name,
                description=description,
                vertical=vertical,
                command=COMMAND_MAP.get(skill_slug),
                raw_prompt=content,
                file_path=skill_file,
            )
            registry[skill_slug] = skill
    return registry


def get_skills_by_vertical(
    registry: dict[str, Skill],
) -> dict[str, list[Skill]]:
    """Group skills by vertical."""
    grouped: dict[str, list[Skill]] = {}
    for skill in registry.values():
        grouped.setdefault(skill.vertical, []).append(skill)
    return grouped
