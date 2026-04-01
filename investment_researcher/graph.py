import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from agents.numbers_agent import run_numbers_agent
from agents.news_agent import run_news_agent
from agents.sec_agent import run_sec_agent
from agents.report_agent import run_report_agent

load_dotenv()


class AgentResult(TypedDict):
    agent: str    # "numbers" | "news" | "sec"
    data: dict
    status: str   # "complete" | "error" | "skipped"
    error: str


class SupervisorState(TypedDict):
    ticker: str
    agent_results: Annotated[list, operator.add]  # 병렬 결과 자동 누적
    report: str


def supervisor_node(state: SupervisorState) -> dict:
    """ticker를 정규화하고 리서치를 시작합니다."""
    ticker = state["ticker"].strip().upper()
    print(f"[Supervisor] {ticker} 리서치 시작 — 3개 에이전트 병렬 실행")
    return {"ticker": ticker}


def fan_out(state: SupervisorState) -> list[Send]:
    """3개 리서치 에이전트를 병렬로 디스패치합니다."""
    ticker = state["ticker"]
    return [
        Send("numbers_agent", {"ticker": ticker}),
        Send("news_agent",    {"ticker": ticker}),
        Send("sec_agent",     {"ticker": ticker}),
    ]


# 그래프 구성
builder = StateGraph(SupervisorState)

builder.add_node("supervisor",    supervisor_node)
builder.add_node("numbers_agent", run_numbers_agent)
builder.add_node("news_agent",    run_news_agent)
builder.add_node("sec_agent",     run_sec_agent)
builder.add_node("report_agent",  run_report_agent)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", fan_out)  # 병렬 fan-out

# 3개 에이전트 완료 후 report_agent 실행 (LangGraph 자동 barrier)
builder.add_edge("numbers_agent", "report_agent")
builder.add_edge("news_agent",    "report_agent")
builder.add_edge("sec_agent",     "report_agent")
builder.add_edge("report_agent",  END)

graph = builder.compile()


def run_research(ticker: str) -> dict:
    """동기 실행 헬퍼. 전체 결과를 반환합니다."""
    initial_state = {
        "ticker": ticker,
        "agent_results": [],
        "report": "",
    }
    return graph.invoke(initial_state)


if __name__ == "__main__":
    result = run_research("AAPL")
    print("\n" + "=" * 60)
    print(result["report"])
