from agents import Agent, RunContextWrapper
from models import UserAccountContext
from guardrails import input_guardrail, output_guardrail

def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext]):

    return """
    당신은 테이블 예약을 받는 직원입니다.
    손님에게 인원수, 희망 날짜, 희망 시간을 순서대로 묻고 예약을 진행하세요.
    희망 시간이 마감되었거나 예약이 불가하면 대안 시간을 제안하세요.
    예약이 완료되면 날짜, 시간, 인원수를 다시 한 번 확인해 주세요.
    친절하고 정확한 안내로 손님이 예약을 확실히 이해했는지 확인하세요.
    고객이 메뉴/재료 문의를 하면 Menu Agent로, 주문을 원하면 Order Management Agent로, 불만/클레임을 말하면 Complaints Agent로 handoff하고 연결 사유를 명시하세요.
    """

reservation_agent = Agent(
    name="Reservation Agent",
    instructions=dynamic_reservation_agent_instructions,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
    handoffs=[],
)