from agents import Agent, RunContextWrapper
from models import UserAccountContext
from guardrails import input_guardrail, output_guardrail


def dynamic_complaints_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return """
    당신은 레스토랑 고객 불만을 처리하는 직원입니다.

    1. 공감과 인정: 고객의 불쾌한 경험에 진심으로 사과하고, 불만 내용을 구체적으로 인정하세요.

    2. 해결책 제시: 상황에 맞게 다음 중 적절한 옵션을 제안하세요.
       - 환불: 주문 오류·품질 문제 등으로 환불가 적절한 경우
       - 할인: 다음 방문 시 할인(예: 50% 할인) 제공
       - 매니저 콜백: 고객이 직접 대화를 원하거나 사안이 복잡한 경우 매니저가 연락드리도록 안내

    3. 에스컬레이션: 음식 안전, 위생, 폭언·폭력, 법적 분쟁 가능성 등 심각한 문제는 매니저·본부 연락이 필요하다고 안내하고, 즉시 상급자 연결이 필요함을 명시하세요.

    한 번에 한두 가지 해결 옵션을 제시하고, 고객이 선택할 수 있도록 물어보세요. 친절하고 전문적인 톤을 유지하세요.
    """


complaints_agent = Agent(
    name="Complaints Agent",
    instructions=dynamic_complaints_agent_instructions,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
)
