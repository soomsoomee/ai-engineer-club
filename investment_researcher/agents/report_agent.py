from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

SYSTEM_PROMPT = """당신은 기관 투자자를 위한 주식 리서치 보고서를 작성하는 시니어 애널리스트입니다.

보고서는 반드시 한국어로 작성하고, 아래 구조를 따르세요:

# [회사명] 투자 리서치 보고서

## 1. 기업 개요
회사 소개, 섹터, 시장 내 포지션을 간략히 설명합니다.

## 2. 기술적 분석
가격 흐름, 이동평균선, RSI, MACD, 볼린저밴드를 분석합니다. 주요 지지/저항 수준과 추세 방향을 명시합니다.

## 3. 최근 뉴스 및 시장 심리
주요 최근 이슈와 주가에 미치는 영향을 요약합니다.

## 4. SEC 10-Q 공시 분석 (해당시)
최근 분기 보고서의 주요 재무 지표, 경영진 전망, 리스크를 정리합니다.

## 5. 투자 의견
모든 분석을 종합하여 아래 형식으로 작성합니다:

**투자등급:** Buy / Neutral / Sell 중 하나
**종합점수:** X / 100점
(점수 기준: 기술적 분석 40점 + 뉴스/시장심리 30점 + 펀더멘털/10-Q 30점)

각 항목별 점수와 산정 근거를 간략히 설명하고, 전체 투자 의견 요약 및 주요 리스크를 명시합니다.
점수 가이드: 70점 이상 Buy, 40~69점 Neutral, 39점 이하 Sell

중요 규칙:
- 숫자와 수치는 절대 백틱(`)으로 감싸지 마세요. 일반 텍스트로 작성하세요.
- 코드 블록을 사용하지 마세요.
- 구체적인 수치를 포함하되 간결하게 작성하세요."""


def _format_technical_section(numbers_data: dict) -> str:
    stock = numbers_data.get("stock_data", {})
    ind = numbers_data.get("indicators", {})
    info = stock.get("info", {})

    company_name = info.get("longName", "N/A")
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    market_cap = info.get("marketCap", 0)
    currency = info.get("currency", "USD")
    pe = info.get("trailingPE", None)
    div_yield = info.get("dividendYield", None)
    week52_high = info.get("fiftyTwoWeekHigh", None)
    week52_low = info.get("fiftyTwoWeekLow", None)

    market_cap_str = f"{market_cap / 1e9:.1f}B {currency}" if market_cap else "N/A"
    pe_str = f"{pe:.1f}" if pe else "N/A"
    div_str = f"{div_yield * 100:.2f}%" if div_yield else "N/A"
    high_str = f"{week52_high}" if week52_high else "N/A"
    low_str = f"{week52_low}" if week52_low else "N/A"

    section = f"""**Company:** {company_name}
**Sector:** {sector} | **Industry:** {industry}
**Market Cap:** {market_cap_str} | **P/E:** {pe_str} | **Dividend Yield:** {div_str}
**52W High:** {high_str} | **52W Low:** {low_str}

**Technical Indicators:**
- Current Price: {ind.get('current_price', 'N/A')} ({ind.get('price_change_pct', 0):+.2f}% vs prev)
- MA20: {ind.get('MA20', 'N/A')} | MA60: {ind.get('MA60', 'N/A')} → Trend: {ind.get('ma_trend', 'N/A')}
- RSI(14): {ind.get('RSI14', 'N/A')} → Signal: {ind.get('rsi_signal', 'N/A')}
- MACD Histogram: {ind.get('MACD_hist', 'N/A')} → Signal: {ind.get('macd_signal', 'N/A')}
- Bollinger Bands: Upper {ind.get('BB_upper', 'N/A')} / Mid {ind.get('BB_mid', 'N/A')} / Lower {ind.get('BB_lower', 'N/A')}
- BB Position: {ind.get('BB_position_pct', 'N/A')}%

**Recent 5-Day Price History:**"""

    for day in ind.get("recent_5days", []):
        section += f"\n- {day['Date']}: Close {day['Close']} | Volume {day['Volume']:,} | MA20 {day.get('MA20', 'N/A')} | RSI {day.get('RSI14', 'N/A')}"

    return section


def _format_news_section(news_data: dict) -> str:
    query = news_data.get("news_query", "")
    items = news_data.get("news_items", [])

    section = f"**Search Query:** {query}\n\n**Recent Articles:**"
    for i, item in enumerate(items[:8], 1):
        section += f"\n{i}. [{item['title']}] — {item['source']} ({item['pubDate']})"

    return section


def _format_sec_section(sec_data: dict) -> str:
    return (
        f"**Company:** {sec_data.get('company_name', 'N/A')}\n"
        f"**Filing Date:** {sec_data.get('filing_date', 'N/A')}\n\n"
        f"{sec_data.get('analysis', '')}"
    )


def run_report_agent(state: dict) -> dict:
    ticker = state["ticker"]
    agent_results = state.get("agent_results", [])
    print(f"[Report Agent] {ticker} 최종 보고서 생성 중...")

    results_map = {r["agent"]: r for r in agent_results}

    context_parts = [f"**Ticker:** {ticker}\n"]

    # Numbers (기술 분석)
    numbers_result = results_map.get("numbers", {})
    if numbers_result.get("status") == "complete":
        context_parts.append("## Technical Analysis Data\n" + _format_technical_section(numbers_result["data"]))
    else:
        context_parts.append(f"## Technical Analysis\n[데이터 없음: {numbers_result.get('error', 'unknown')}]")

    # News
    news_result = results_map.get("news", {})
    if news_result.get("status") == "complete":
        context_parts.append("## News Data\n" + _format_news_section(news_result["data"]))
    else:
        context_parts.append(f"## News\n[데이터 없음: {news_result.get('error', 'unknown')}]")

    # SEC 10-Q
    sec_result = results_map.get("sec", {})
    if sec_result.get("status") == "complete":
        context_parts.append("## SEC 10-Q Filing Data\n" + _format_sec_section(sec_result["data"]))
    elif sec_result.get("status") == "skipped":
        context_parts.append(f"## SEC 10-Q Filing\n[해당 없음: {sec_result.get('error', '')}]")
    else:
        context_parts.append(f"## SEC 10-Q Filing\n[데이터 없음: {sec_result.get('error', 'unknown')}]")

    full_context = "\n\n".join(context_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=full_context),
    ]
    response = llm.invoke(messages)
    print(f"[Report Agent] 완료 — {len(response.content):,} chars")

    return {"report": response.content}
