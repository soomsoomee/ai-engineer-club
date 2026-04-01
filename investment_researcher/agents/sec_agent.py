import json
import re
import urllib.request
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

SEC_HEADERS = {"User-Agent": "InvestmentResearcher researcher@example.com"}


class AgentState(TypedDict):
    ticker: str


def _get_cik(ticker: str) -> tuple:
    """SEC EDGAR에서 ticker의 CIK와 회사명을 조회합니다."""
    # 비미국 종목 체크 (.KS, .T, .L 등)
    if "." in ticker:
        raise ValueError(f"{ticker}는 미국 상장 종목이 아닙니다. SEC 10-Q 조회를 건너뜁니다.")

    url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return entry["cik_str"], entry["title"]

    raise ValueError(f"SEC EDGAR에서 {ticker} 종목을 찾을 수 없습니다.")


def _get_latest_10q_info(cik: int) -> tuple:
    """최신 10-Q 파일의 accession number, primary document, 제출일을 반환합니다."""
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    filings = data["filings"]["recent"]
    for i, form in enumerate(filings["form"]):
        if form == "10-Q":
            return (
                filings["accessionNumber"][i],
                filings["primaryDocument"][i],
                filings["filingDate"][i],
            )

    raise ValueError(f"CIK {cik}에 대한 10-Q 파일을 찾을 수 없습니다.")


def _fetch_10q_text(cik: int, accession: str, primary_doc: str) -> str:
    """10-Q iXBRL HTML을 다운로드하고 핵심 텍스트를 추출합니다."""
    accession_clean = accession.replace("-", "")
    url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/"
        f"{accession_clean}/{primary_doc}"
    )
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw_html = r.read().decode("utf-8", errors="replace")

    # HTML 정리: script/style 제거 → HTML 엔티티 제거 → 태그 제거 → 공백 정규화
    text = re.sub(
        r"<(script|style)[^>]*>.*?</(script|style)>",
        " ", raw_html, flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"&[^;]{1,8};", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # XBRL 메타데이터 앞부분 건너뛰기
    for marker in ["UNITED STATES SECURITIES", "FORM 10-Q", "Form 10-Q"]:
        idx = text.find(marker)
        if idx != -1:
            text = text[idx:]
            break

    # 전략: 요약 섹션(0~8k) + MD&A 섹션(두 번째 등장 이후 15k)
    summary_section = text[:8_000]

    mda_occurrences = [
        m.start() for m in re.finditer(
            r"MANAGEMENT.{1,5}S DISCUSSION AND ANALYSIS",
            text, re.IGNORECASE,
        )
    ]

    if len(mda_occurrences) >= 2:
        mda_start = mda_occurrences[1]
        mda_section = text[mda_start: mda_start + 15_000]
    else:
        mda_section = text[8_000:23_000]

    return summary_section + "\n\n[...]\n\n" + mda_section


def run_sec_agent(state: AgentState) -> dict:
    ticker = state["ticker"]
    print(f"[SEC Agent] {ticker} 10-Q 분석 시작...")
    try:
        cik, company_name = _get_cik(ticker)
        print(f"[SEC Agent] CIK: {cik}, 회사명: {company_name}")

        accession, primary_doc, filing_date = _get_latest_10q_info(cik)
        print(f"[SEC Agent] 최신 10-Q: {filing_date} ({accession})")

        filing_text = _fetch_10q_text(cik, accession, primary_doc)
        print(f"[SEC Agent] 텍스트 추출 완료 ({len(filing_text):,} chars) — LLM 분석 중...")

        messages = [
            SystemMessage(content=(
                "You are a senior financial analyst. Analyze this SEC 10-Q filing and provide a structured summary:\n"
                "1. **Revenue & Profit**: Key financial figures with YoY comparison\n"
                "2. **Segment Performance**: Business segment highlights\n"
                "3. **Management Outlook**: Forward guidance and strategic priorities\n"
                "4. **Key Risks**: Top 3 risk factors mentioned\n"
                "5. **Notable Items**: Significant one-time events or changes\n\n"
                "Be concise and factual. Use English."
            )),
            HumanMessage(content=(
                f"Company: {company_name} ({ticker})\n"
                f"Filing: 10-Q, period ending {filing_date}\n\n"
                f"{filing_text}"
            )),
        ]
        response = llm.invoke(messages)
        print(f"[SEC Agent] 완료")

        return {
            "agent_results": [{
                "agent": "sec",
                "data": {
                    "company_name": company_name,
                    "filing_date": filing_date,
                    "accession": accession,
                    "analysis": response.content,
                },
                "status": "complete",
                "error": "",
            }]
        }

    except ValueError as e:
        # 비미국 종목 등 예상된 케이스 → skipped
        print(f"[SEC Agent] 건너뜀: {e}")
        return {
            "agent_results": [{
                "agent": "sec",
                "data": {},
                "status": "skipped",
                "error": str(e),
            }]
        }
    except Exception as e:
        print(f"[SEC Agent] 오류: {e}")
        return {
            "agent_results": [{
                "agent": "sec",
                "data": {},
                "status": "error",
                "error": str(e),
            }]
        }
