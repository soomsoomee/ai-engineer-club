import json
import os
import queue
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st

from agents.chat_agent import handle_chat_query
from graph import graph

# ─── 상수 ─────────────────────────────────────────────────────
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

AGENT_META = {
    "supervisor":    {"label": "Supervisor",                        "icon": "🎯"},
    "numbers_agent": {"label": "Numbers Agent (Technical Analysis)", "icon": "📊"},
    "news_agent":    {"label": "News Agent (Market News)",           "icon": "📰"},
    "sec_agent":     {"label": "SEC 10-Q Agent (Filings)",           "icon": "📄"},
    "report_agent":  {"label": "Report Agent (Final Report)",        "icon": "📝"},
}
RESEARCH_AGENTS = ["numbers_agent", "news_agent", "sec_agent"]
ALL_AGENTS = ["supervisor"] + RESEARCH_AGENTS + ["report_agent"]


# ─── 보고서 저장/로드 헬퍼 ────────────────────────────────────
def _save_report(ticker: str, report: str, agent_statuses: dict) -> Path:
    """보고서를 JSON 파일로 저장하고 파일 경로를 반환합니다."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"{ticker}_{ts}.json"
    payload = {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "report": report,
        "agent_statuses": agent_statuses,
    }
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _list_reports() -> list[Path]:
    """저장된 보고서를 최신순으로 반환합니다."""
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    return files


def _format_report_label(path: Path) -> str:
    """파일명에서 ticker + 날짜 레이블을 생성합니다."""
    stem = path.stem  # e.g. "AAPL_20250401_153000"
    parts = stem.split("_", 1)
    if len(parts) == 2:
        ticker, ts = parts
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            return f"{ticker}  ·  {dt.strftime('%Y-%m-%d %H:%M')}"
        except ValueError:
            pass
    return stem


# ─── 그래프 실행 스레드 ───────────────────────────────────────
def _run_graph_in_thread(ticker: str, event_queue: queue.Queue):
    try:
        for chunk in graph.stream(
            {"ticker": ticker, "agent_results": [], "report": ""},
            stream_mode="updates",
        ):
            event_queue.put({"type": "update", "chunk": chunk})
        event_queue.put({"type": "done"})
    except Exception as e:
        event_queue.put({"type": "error", "error": str(e)})


# ─── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="Investment Research System",
    page_icon="📈",
    layout="wide",
)

# ─── 사이드바: 과거 보고서 ────────────────────────────────────
with st.sidebar:
    st.header("📂 Past Reports")
    past_reports = _list_reports()

    if not past_reports:
        st.caption("저장된 보고서가 없습니다.")
    else:
        for rpt_path in past_reports:
            label = _format_report_label(rpt_path)
            if st.button(label, key=str(rpt_path), use_container_width=True):
                st.session_state["viewing_report"] = str(rpt_path)
                st.session_state.pop("running", None)

    if past_reports:
        st.divider()
        if st.button("새 리서치 작성", use_container_width=True):
            st.session_state.pop("viewing_report", None)

# ─── 메인 영역 ────────────────────────────────────────────────
st.title("📈 Investment Research System")
st.caption("3개 리서치 에이전트가 병렬로 분석 후 최종 보고서를 생성합니다.")

# 과거 보고서 조회 모드
if "viewing_report" in st.session_state:
    rpt = _load_report(Path(st.session_state["viewing_report"]))
    dt_str = datetime.fromisoformat(rpt["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    st.subheader(f"📋 {rpt['ticker']} — {dt_str}")

    # 에이전트 상태 요약
    statuses = rpt.get("agent_statuses", {})
    if statuses:
        cols = st.columns(len(statuses))
        for i, (agent_key, status_str) in enumerate(statuses.items()):
            meta = AGENT_META.get(agent_key, {"icon": "•", "label": agent_key})
            with cols[i]:
                st.markdown(f"**{meta['icon']} {meta['label']}**\n\n{status_str}")

    st.divider()
    st.markdown(rpt["report"])

    # ─── 채팅 섹션 ────────────────────────────────────────────
    st.divider()
    st.subheader("💬 보고서 관련 질문")
    st.caption("보고서 내용을 바탕으로 추가 질문을 해보세요. 최신 정보가 필요한 경우 자동으로 검색합니다.")

    chat_key = f"chat_{st.session_state['viewing_report']}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # 이전 대화 표시
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            if msg.get("is_guardrail"):
                st.warning(msg["content"])
            elif msg.get("is_error"):
                st.error(msg["content"])
            else:
                st.markdown(msg["content"])
            if msg.get("search_results"):
                with st.expander("🔍 검색된 최신 뉴스 출처"):
                    for item in msg["search_results"]:
                        st.markdown(f"- [{item['title']}]({item['link']}) — {item['source']} ({item['pubDate']})")

    # 채팅 입력
    if prompt := st.chat_input("보고서 내용에 대해 질문해보세요..."):
        st.session_state[chat_key].append({"role": "user", "content": prompt})

        with st.spinner("분석 중..."):
            result = handle_chat_query(
                question=prompt,
                report=rpt["report"],
                ticker=rpt["ticker"],
                chat_history=st.session_state[chat_key][:-1],
            )

        if result["error"] == "guardrail":
            st.session_state[chat_key].append({
                "role": "assistant",
                "content": result["answer"],
                "is_guardrail": True,
                "search_results": [],
            })
        elif result["error"]:
            st.session_state[chat_key].append({
                "role": "assistant",
                "content": f"오류가 발생했습니다: {result['error']}",
                "is_error": True,
                "search_results": [],
            })
        else:
            st.session_state[chat_key].append({
                "role": "assistant",
                "content": result["answer"],
                "search_results": result.get("search_results", []),
            })

        st.rerun()

    st.stop()

# 신규 리서치 모드
col_input, col_btn = st.columns([3, 1])
with col_input:
    ticker_input = st.text_input(
        "Ticker Symbol",
        value="AAPL",
        max_chars=20,
        placeholder="예: AAPL, MSFT, TSLA",
        label_visibility="collapsed",
    )
with col_btn:
    is_running = st.session_state.get("running", False)
    run_button = st.button(
        "Research" if not is_running else "Running...",
        type="primary",
        use_container_width=True,
        disabled=is_running,
    )

st.divider()

if run_button and ticker_input.strip():
    ticker = ticker_input.strip().upper()
    st.session_state["running"] = True

    # 에이전트 상태 표시
    st.subheader("Agent Status")
    status_cols = st.columns(len(ALL_AGENTS))
    placeholders = {}
    for i, agent_key in enumerate(ALL_AGENTS):
        with status_cols[i]:
            meta = AGENT_META[agent_key]
            ph = st.empty()
            ph.markdown(f"**{meta['icon']} {meta['label']}**\n\n⏳ waiting")
            placeholders[agent_key] = ph

    st.divider()
    report_header = st.empty()
    report_placeholder = st.empty()

    # 백그라운드 스레드 시작
    event_q: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=_run_graph_in_thread,
        args=(ticker, event_q),
        daemon=True,
    )
    thread.start()

    # 에이전트 완료 상태 수집 (저장용)
    agent_statuses: dict[str, str] = {}

    while True:
        try:
            event = event_q.get(timeout=0.1)
        except queue.Empty:
            continue

        if event["type"] == "error":
            st.error(f"오류 발생: {event['error']}")
            break

        if event["type"] == "done":
            break

        chunk = event["chunk"]
        node_name = next(iter(chunk))
        node_data = chunk[node_name]

        if node_name not in AGENT_META:
            continue

        meta = AGENT_META[node_name]

        if node_name == "supervisor":
            status_str = "✅ complete"
            placeholders["supervisor"].markdown(f"**{meta['icon']} {meta['label']}**\n\n{status_str}")
            agent_statuses["supervisor"] = status_str
            for ag in RESEARCH_AGENTS:
                ag_meta = AGENT_META[ag]
                placeholders[ag].markdown(f"**{ag_meta['icon']} {ag_meta['label']}**\n\n🔄 running...")

        elif node_name in RESEARCH_AGENTS:
            results = node_data.get("agent_results", [])
            if results:
                status = results[0].get("status", "complete")
                status_str = {"complete": "✅ complete", "skipped": "⏭️ skipped"}.get(status, "❌ error")
            else:
                status_str = "✅ complete"
            placeholders[node_name].markdown(f"**{meta['icon']} {meta['label']}**\n\n{status_str}")
            agent_statuses[node_name] = status_str

        elif node_name == "report_agent":
            placeholders["report_agent"].markdown(f"**{meta['icon']} {meta['label']}**\n\n🔄 running...")
            report_text = node_data.get("report", "")
            if report_text:
                status_str = "✅ complete"
                placeholders["report_agent"].markdown(f"**{meta['icon']} {meta['label']}**\n\n{status_str}")
                agent_statuses["report_agent"] = status_str

                # 보고서 저장
                saved_path = _save_report(ticker, report_text, agent_statuses)

                report_header.subheader(f"📋 Investment Analysis Report — {ticker}")
                report_placeholder.markdown(report_text)
                st.toast(f"보고서가 저장되었습니다: {saved_path.name}", icon="💾")

    thread.join(timeout=5)
    st.session_state["running"] = False
    st.rerun()
