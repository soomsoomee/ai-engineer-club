from agents import Agent, RunContextWrapper
from models import UserAccountContext
from guardrails import input_guardrail, output_guardrail

def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext]):

    return f"""
    당신은 레스토랑에서 주문을 받는 직원입니다.
    손님에게 메뉴를 안내하고, 원하는 메뉴와 수량, 옵션(맵기, 얼음 등)을 확인하세요.
    주문 내용을 한 번 더 읽어주며 최종 확인하고, 예상 대기 시간이 있으면 안내하세요.
    알레르기가 있다고 하면 해당 메뉴의 재료를 꼼꼼히 확인한 뒤 안내하세요.
    주문이 완료되면 감사 인사와 함께 마무리하세요.
    """

order_agent = Agent(
    name="Order Management Agent",
    instructions=dynamic_order_agent_instructions,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
)