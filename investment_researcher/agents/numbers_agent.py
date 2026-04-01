import os
from typing import TypedDict

import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


class AgentState(TypedDict):
    ticker: str


@tool
def get_stock_data(ticker: str) -> dict:
    """주식 데이터를 가져옵니다. ticker는 주식 심볼입니다 (예: AAPL, 005930.KS)."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")

    records = []
    for date, row in hist.iterrows():
        records.append({
            "Date": date.strftime("%Y-%m-%d"),
            "Open": round(float(row["Open"]), 2),
            "High": round(float(row["High"]), 2),
            "Low": round(float(row["Low"]), 2),
            "Close": round(float(row["Close"]), 2),
            "Volume": int(row["Volume"]),
        })

    info = stock.info
    company_info = {
        "longName": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "marketCap": info.get("marketCap", 0),
        "trailingPE": info.get("trailingPE", None),
        "dividendYield": info.get("dividendYield", None),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", None),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", None),
        "currency": info.get("currency", "USD"),
    }

    return {"history": records, "info": company_info}


def _calculate_indicators(history: list) -> dict:
    """히스토리 데이터로 기술 지표를 계산합니다."""
    df = pd.DataFrame(history)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Moving Averages
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()

    # RSI(14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    # MACD (12-26-9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands (20일, ±2σ)
    df["BB_mid"] = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * bb_std
    df["BB_lower"] = df["BB_mid"] - 2 * bb_std

    last = df.iloc[-1]
    current_price = float(last["Close"])
    prev_price = float(df.iloc[-2]["Close"]) if len(df) > 1 else current_price
    price_change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0

    rsi_val = float(last["RSI14"]) if pd.notna(last["RSI14"]) else 50.0
    rsi_signal = "과매수" if rsi_val >= 70 else ("과매도" if rsi_val <= 30 else "중립")

    macd_hist_val = float(last["MACD_hist"]) if pd.notna(last["MACD_hist"]) else 0.0
    macd_signal_str = "강세" if macd_hist_val > 0 else "약세"

    ma20_val = float(last["MA20"]) if pd.notna(last["MA20"]) else current_price
    ma60_val = float(last["MA60"]) if pd.notna(last["MA60"]) else current_price
    ma_trend = "상승추세" if current_price > ma20_val > ma60_val else "하락추세"

    bb_upper = float(last["BB_upper"]) if pd.notna(last["BB_upper"]) else current_price
    bb_lower = float(last["BB_lower"]) if pd.notna(last["BB_lower"]) else current_price
    bb_range = bb_upper - bb_lower
    bb_position_pct = ((current_price - bb_lower) / bb_range * 100) if bb_range > 0 else 50.0

    recent_5 = []
    for date, row in df.tail(5).iterrows():
        recent_5.append({
            "Date": date.strftime("%Y-%m-%d"),
            "Close": round(float(row["Close"]), 2),
            "Volume": int(row["Volume"]),
            "MA20": round(float(row["MA20"]), 2) if pd.notna(row["MA20"]) else None,
            "RSI14": round(float(row["RSI14"]), 2) if pd.notna(row["RSI14"]) else None,
        })

    return {
        "current_price": round(current_price, 2),
        "price_change_pct": round(price_change_pct, 2),
        "MA20": round(ma20_val, 2),
        "MA60": round(ma60_val, 2),
        "RSI14": round(rsi_val, 2),
        "MACD_hist": round(macd_hist_val, 4),
        "MACD_signal": round(float(last["MACD_signal"]) if pd.notna(last["MACD_signal"]) else 0.0, 4),
        "BB_upper": round(bb_upper, 2),
        "BB_mid": round(float(last["BB_mid"]) if pd.notna(last["BB_mid"]) else current_price, 2),
        "BB_lower": round(bb_lower, 2),
        "BB_position_pct": round(bb_position_pct, 1),
        "rsi_signal": rsi_signal,
        "macd_signal": macd_signal_str,
        "ma_trend": ma_trend,
        "recent_5days": recent_5,
    }


def run_numbers_agent(state: AgentState) -> dict:
    ticker = state["ticker"]
    print(f"[Numbers Agent] {ticker} 기술 분석 시작...")
    try:
        raw = get_stock_data.invoke({"ticker": ticker})
        indicators = _calculate_indicators(raw["history"])
        print(f"[Numbers Agent] 완료 — 현재가: {indicators['current_price']}, RSI: {indicators['RSI14']}")
        return {
            "agent_results": [{
                "agent": "numbers",
                "data": {"stock_data": raw, "indicators": indicators},
                "status": "complete",
                "error": "",
            }]
        }
    except Exception as e:
        print(f"[Numbers Agent] 오류: {e}")
        return {
            "agent_results": [{
                "agent": "numbers",
                "data": {},
                "status": "error",
                "error": str(e),
            }]
        }
