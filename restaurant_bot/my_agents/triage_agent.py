import streamlit as st
from agents import (
    Agent, 
    RunContextWrapper, 
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent
from my_agents.complaints_agent import complaints_agent
from models import UserAccountContext, HandoffData
from guardrails import input_guardrail, output_guardrail


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext]):

    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    당신은 레스토랑 고객 상담의 첫 접점입니다. 고객 메시지를 분석해 의도를 파악하세요.
    메뉴, 재료, 알레르기 관련 질문이면 Menu Agent로, 주문 요청이면 Order Agent로, 테이블 예약이면 Reservation Agent로, 불만·불편·항의·클레임이면 Complaints Agent로 연결하세요.
    고객의 요청이 불명확하면 한두 가지 질문으로 의도를 확인한 뒤 담당 에이전트로 넘기세요.
    연결 시 handoff를 사용하고, 연결 사유를 간단히 명시하세요.
    """

def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools
    )


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData):
    with st.sidebar:
        st.write(f"""
        Handing off to {input_data.to_agent_name}
        Reason: {input_data.reason}
        Issue type: {input_data.issue_type}
        Issue description: {input_data.issue_description}
        """)

triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(reservation_agent),
        make_handoff(order_agent),
        make_handoff(complaints_agent),
    ]
)