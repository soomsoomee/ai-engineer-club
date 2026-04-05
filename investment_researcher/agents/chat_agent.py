import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

_GUARDRAIL_PROMPT = """당신은 투자 리서치 질문 분류기입니다.
사용자의 질문이 투자, 주식, 기업, 재무, 시장, 경제, 산업 분석과 관련이 있는지 판단하세요.

관련 있으면 "YES", 관련 없으면 "NO"만 답하세요. 다른 말은 하지 마세요."""

_SEARCH_DECISION_PROMPT = """당신은 투자 리서치 어시스턴트입니다.
아래 보고서와 질문을 보고, 보고서에 없는 최신 정보(최근 뉴스, 최근 주가, 최신 공시 등)가 필요한지 판단하세요.

필요하면 "YES", 보고서만으로 충분하면 "NO"만 답하세요. 다른 말은 하지 마세요.

[보고서 요약]
{report_summary}

[질문]
{question}"""

_ANSWER_SYSTEM_PROMPT = """당신은 투자 리서치 보고서 전문 분석가입니다.
아래 보고서 내용을 기반으로 사용자의 질문에 정확하고 유익하게 답변하세요.

규칙:
- 보고서에 있는 정보를 우선적으로 활용하세요.
- 추가 검색 결과가 있다면 함께 활용하세요.
- 구체적인 수치나 근거를 포함해 답변하세요.
- 코드 블록이나 백틱은 사용하지 마세요.
- 한국어로 답변하세요.

[보고서 내용]
{report}
"""


def _search_news(query: str) -> list[dict]:
    """Google News RSS로 뉴스를 검색합니다."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        xml_content = response.read()

    root = ET.fromstring(xml_content)
    channel = root.find("channel")
    items = []
    for item in channel.findall("item")[:5]:
        title = item.findtext("title", "")
        pub_date = item.findtext("pubDate", "")
        link = item.findtext("link", "")
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Unknown"
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            pub_date = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        items.append({"title": title, "pubDate": pub_date, "link": link, "source": source})
    return items


def _search_with_fallback(ticker: str) -> list[dict]:
    """쿼리 후보를 순서대로 시도해 결과가 있는 첫 번째를 반환합니다."""
    candidates = [f"{ticker} stock", ticker]
    for query in candidates:
        try:
            items = _search_news(query)
            if items:
                return items
        except Exception:
            continue
    return []


def handle_chat_query(
    question: str,
    report: str,
    ticker: str,
    chat_history: list[dict],
) -> dict:
    """
    보고서 기반 추가 질의를 처리합니다.

    Returns:
        {
            "answer": str,
            "used_search": bool,
            "search_results": list,
            "error": str | None,  # "guardrail" | error message | None
        }
    """
    # 1. 가드레일: 투자 관련 질문인지 확인
    try:
        guardrail_resp = llm.invoke([
            SystemMessage(content=_GUARDRAIL_PROMPT),
            HumanMessage(content=question),
        ])
        is_relevant = guardrail_resp.content.strip().upper().startswith("YES")
    except Exception as e:
        return {
            "answer": "",
            "used_search": False,
            "search_results": [],
            "error": f"가드레일 확인 중 오류가 발생했습니다: {e}",
        }

    if not is_relevant:
        return {
            "answer": "투자 리서치와 관련된 질문만 답변드릴 수 있습니다. 주식, 기업, 재무, 시장 분석 등에 관해 질문해 주세요.",
            "used_search": False,
            "search_results": [],
            "error": "guardrail",
        }

    # 2. 웹 검색 필요 여부 판단
    report_summary = report[:1000]
    try:
        search_decision_resp = llm.invoke([
            SystemMessage(content=_SEARCH_DECISION_PROMPT.format(
                report_summary=report_summary,
                question=question,
            )),
            HumanMessage(content="검색이 필요한가요?"),
        ])
        needs_search = search_decision_resp.content.strip().upper().startswith("YES")
    except Exception:
        needs_search = False

    search_results = []
    search_context = ""
    if needs_search:
        try:
            search_results = _search_with_fallback(ticker)
            if search_results:
                lines = [f"{i+1}. [{item['title']}] — {item['source']} ({item['pubDate']})"
                         for i, item in enumerate(search_results)]
                search_context = "\n\n[최신 검색 결과]\n" + "\n".join(lines)
        except Exception:
            search_results = []

    # 3. 답변 생성
    system_content = _ANSWER_SYSTEM_PROMPT.format(report=report)
    messages = [SystemMessage(content=system_content)]

    # 대화 이력 추가
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=msg["content"]))

    user_content = question
    if search_context:
        user_content += search_context

    messages.append(HumanMessage(content=user_content))

    try:
        response = llm.invoke(messages)
        return {
            "answer": response.content,
            "used_search": bool(search_results),
            "search_results": search_results,
            "error": None,
        }
    except Exception as e:
        return {
            "answer": "",
            "used_search": False,
            "search_results": [],
            "error": f"답변 생성 중 오류가 발생했습니다: {e}",
        }
