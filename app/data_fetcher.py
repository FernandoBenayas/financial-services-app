"""Fetch real-time financial data from the web (yfinance + DuckDuckGo search)."""

from __future__ import annotations

import traceback
from dataclasses import dataclass

import yfinance as yf
from duckduckgo_search import DDGS


@dataclass
class CompanyData:
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float | None
    currency: str
    price: float | None
    pe_ratio: float | None
    forward_pe: float | None
    ev_ebitda: float | None
    price_to_book: float | None
    dividend_yield: float | None
    beta: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    revenue: float | None
    net_income: float | None
    ebitda: float | None
    total_debt: float | None
    total_cash: float | None
    shares_outstanding: float | None
    summary: str
    raw: dict


def fetch_company_data(ticker: str) -> CompanyData | None:
    """Fetch comprehensive company data from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return None

        return CompanyData(
            ticker=ticker.upper(),
            name=info.get("longName", info.get("shortName", ticker)),
            sector=info.get("sector", "N/A"),
            industry=info.get("industry", "N/A"),
            market_cap=info.get("marketCap"),
            currency=info.get("currency", "USD"),
            price=info.get("regularMarketPrice") or info.get("currentPrice"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            price_to_book=info.get("priceToBook"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            revenue=info.get("totalRevenue"),
            net_income=info.get("netIncomeToCommon"),
            ebitda=info.get("ebitda"),
            total_debt=info.get("totalDebt"),
            total_cash=info.get("totalCash"),
            shares_outstanding=info.get("sharesOutstanding"),
            summary=info.get("longBusinessSummary", ""),
            raw=info,
        )
    except Exception:
        traceback.print_exc()
        return None


def fetch_financials(ticker: str) -> dict:
    """Fetch income statement, balance sheet, and cash flow data."""
    try:
        t = yf.Ticker(ticker)
        result: dict = {}

        inc = t.income_stmt
        if inc is not None and not inc.empty:
            result["income_statement"] = _df_to_dict(inc)

        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            result["balance_sheet"] = _df_to_dict(bs)

        cf = t.cashflow
        if cf is not None and not cf.empty:
            result["cash_flow"] = _df_to_dict(cf)

        return result
    except Exception:
        traceback.print_exc()
        return {}


def fetch_earnings_history(ticker: str) -> list[dict]:
    """Fetch recent earnings history (actual vs estimate)."""
    try:
        t = yf.Ticker(ticker)
        eh = t.earnings_history
        if eh is not None and not eh.empty:
            return eh.to_dict("records")
        return []
    except Exception:
        return []


def fetch_peer_data(tickers: list[str]) -> list[CompanyData]:
    """Fetch data for multiple tickers (for comps analysis)."""
    results = []
    for tick in tickers:
        data = fetch_company_data(tick.strip())
        if data:
            results.append(data)
    return results


def search_web(query: str, max_results: int = 8) -> list[dict]:
    """Search the web for financial information."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [{"title": r["title"], "body": r["body"], "url": r["href"]} for r in results]
    except Exception:
        traceback.print_exc()
        return []


def search_news(query: str, max_results: int = 8) -> list[dict]:
    """Search for recent news articles."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "url": r.get("url", ""),
                    "date": r.get("date", ""),
                    "source": r.get("source", ""),
                }
                for r in results
            ]
    except Exception:
        traceback.print_exc()
        return []


def format_company_summary(data: CompanyData) -> str:
    """Format company data into a readable summary for the LLM."""

    def _fmt_num(val: float | None, prefix: str = "$", suffix: str = "") -> str:
        if val is None:
            return "N/A"
        if abs(val) >= 1e12:
            return f"{prefix}{val / 1e12:.2f}T{suffix}"
        if abs(val) >= 1e9:
            return f"{prefix}{val / 1e9:.2f}B{suffix}"
        if abs(val) >= 1e6:
            return f"{prefix}{val / 1e6:.1f}M{suffix}"
        return f"{prefix}{val:,.0f}{suffix}"

    def _fmt_pct(val: float | None) -> str:
        if val is None:
            return "N/A"
        return f"{val * 100:.1f}%" if abs(val) < 1 else f"{val:.1f}%"

    lines = [
        f"## {data.name} ({data.ticker})",
        f"**Sector:** {data.sector} | **Industry:** {data.industry}",
        f"**Price:** {data.currency} {data.price} | **Market Cap:** {_fmt_num(data.market_cap)}",
        "",
        "### Valuation Metrics",
        f"- P/E (TTM): {data.pe_ratio:.1f}x" if data.pe_ratio else "- P/E (TTM): N/A",
        f"- Forward P/E: {data.forward_pe:.1f}x" if data.forward_pe else "- Forward P/E: N/A",
        f"- EV/EBITDA: {data.ev_ebitda:.1f}x" if data.ev_ebitda else "- EV/EBITDA: N/A",
        f"- P/B: {data.price_to_book:.1f}x" if data.price_to_book else "- P/B: N/A",
        f"- Dividend Yield: {_fmt_pct(data.dividend_yield)}" if data.dividend_yield else "",
        f"- Beta: {data.beta:.2f}" if data.beta else "",
        "",
        "### Financials",
        f"- Revenue (TTM): {_fmt_num(data.revenue)}",
        f"- EBITDA (TTM): {_fmt_num(data.ebitda)}",
        f"- Net Income (TTM): {_fmt_num(data.net_income)}",
        f"- Total Debt: {_fmt_num(data.total_debt)}",
        f"- Cash: {_fmt_num(data.total_cash)}",
        f"- Shares Outstanding: {_fmt_num(data.shares_outstanding, prefix='')}",
        "",
        f"**52-Week Range:** {data.currency} {data.fifty_two_week_low} – {data.fifty_two_week_high}",
        "",
        f"**Business Summary:** {data.summary[:500]}{'…' if len(data.summary) > 500 else ''}",
    ]
    return "\n".join(line for line in lines if line is not None)


def format_financials_summary(financials: dict) -> str:
    """Format financial statements into a readable table for the LLM."""
    sections = []
    for section_name, data in financials.items():
        if not data:
            continue
        label = section_name.replace("_", " ").title()
        sections.append(f"\n### {label}")
        periods = sorted(data.keys(), reverse=True)[:4]
        for period in periods:
            sections.append(f"\n**{period}:**")
            items = data[period]
            for item_name, value in list(items.items())[:20]:
                if value is not None:
                    if isinstance(value, (int, float)):
                        if abs(value) >= 1e9:
                            formatted = f"${value / 1e9:.2f}B"
                        elif abs(value) >= 1e6:
                            formatted = f"${value / 1e6:.1f}M"
                        else:
                            formatted = f"${value:,.0f}"
                    else:
                        formatted = str(value)
                    sections.append(f"- {item_name}: {formatted}")
    return "\n".join(sections)


def format_news_summary(articles: list[dict]) -> str:
    """Format news articles into a readable summary."""
    if not articles:
        return "No recent news found."
    lines = ["## Recent News & Developments\n"]
    for i, article in enumerate(articles, 1):
        lines.append(f"**{i}. {article['title']}**")
        if article.get("source"):
            lines.append(f"*Source: {article['source']}*" +
                        (f" | *{article['date']}*" if article.get("date") else ""))
        if article.get("body"):
            lines.append(article["body"][:300])
        lines.append(f"[Link]({article.get('url', '')})\n")
    return "\n".join(lines)


def _df_to_dict(df) -> dict:
    """Convert a pandas DataFrame to a serializable dict."""
    result = {}
    for col in df.columns:
        period_label = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
        col_data = {}
        for idx in df.index:
            val = df.at[idx, col]
            if val is not None and str(val) != "nan":
                try:
                    col_data[str(idx)] = float(val)
                except (ValueError, TypeError):
                    col_data[str(idx)] = str(val)
        result[period_label] = col_data
    return result
