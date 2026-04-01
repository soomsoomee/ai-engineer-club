import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import TypedDict

import yfinance as yf
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


class AgentState(TypedDict):
    ticker: str


@tool
def get_rss_news(query: str) -> list:
    """Google News RSS에서 뉴스를 가져옵니다."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        xml_content = response.read()

    root = ET.fromstring(xml_content)
    channel = root.find("channel")

    news_items = []
    for item in channel.findall("item")[:10]:
        title = item.findtext("title", "")
        pub_date = item.findtext("pubDate", "")
        link = item.findtext("link", "")
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Unknown"

        # 날짜 포맷 정리
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            pub_date = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        news_items.append({
            "title": title,
            "pubDate": pub_date,
            "link": link,
            "source": source,
        })

    return news_items


def _get_company_name(ticker: str) -> str:
    """yfinance로 회사명을 빠르게 조회합니다."""
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ""
    except Exception:
        return ""


def _fetch_news_with_fallback(ticker: str, company_name: str) -> tuple[str, list]:
    """쿼리 후보를 순서대로 시도해 결과가 나오는 첫 번째 쿼리를 사용합니다."""
    # 짧고 구체적인 후보 순서대로 시도 (Google News RSS는 키워드가 많으면 결과 0개)
    candidates = []
    if company_name:
        candidates.append(f"{company_name} {ticker}")   # "Circle Internet Group CRCL"
        candidates.append(company_name)                  # "Circle Internet Group"
    candidates.append(f"{ticker} stock")                 # "CRCL stock"
    candidates.append(ticker)                            # "CRCL"

    for query in candidates:
        items = get_rss_news.invoke({"query": query})
        if items:
            return query, items

    return candidates[0], []


def run_news_agent(state: AgentState) -> dict:
    ticker = state["ticker"]
    print(f"[News Agent] {ticker} 뉴스 수집 시작...")
    try:
        company_name = _get_company_name(ticker)
        print(f"[News Agent] 회사명: {company_name or '조회 실패'}")
        query, news_items = _fetch_news_with_fallback(ticker, company_name)
        print(f"[News Agent] 검색 쿼리: {query}")
        print(f"[News Agent] 완료 — {len(news_items)}개 기사 수집")
        return {
            "agent_results": [{
                "agent": "news",
                "data": {"news_query": query, "news_items": news_items},
                "status": "complete",
                "error": "",
            }]
        }
    except Exception as e:
        print(f"[News Agent] 오류: {e}")
        return {
            "agent_results": [{
                "agent": "news",
                "data": {},
                "status": "error",
                "error": str(e),
            }]
        }
