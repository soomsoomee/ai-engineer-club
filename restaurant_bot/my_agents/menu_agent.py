from agents import Agent, RunContextWrapper
from models import UserAccountContext
from guardrails import input_guardrail, output_guardrail

def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext]):

    return f"""
    당신은 레스토랑 메뉴와 음식 정보를 안내하는 직원입니다.
    메뉴 구성, 가격, 재료, 조리법에 대한 질문에 정확히 답변하세요.
    알레르기 관련 질문에는 해당 메뉴의 알레르기 유발 재료를 꼼꼼히 확인해 안전하게 안내하세요.
    정보가 부족하면 추정하지 말고, 가능한 범위에서만 답변하세요.
    친절하고 전문적인 톤으로 답변하세요.
    """

menu_agent = Agent(
    name="Menu Agent",
    instructions=dynamic_menu_agent_instructions,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
)