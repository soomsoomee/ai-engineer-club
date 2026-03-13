from agents import (
    Agent,
    output_guardrail,
    input_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
from models import InputGuardRailOutput, OutputGuardRailOutput, UserAccountContext

input_guardrail_agent = Agent(
    name="Input Guardrail",
    instructions="""
당신은 사용자 입력이 이 레스토랑 봇의 역할 범위 안인지 판단하는 검사자입니다.

역할 범위: 예약, 메뉴 문의, 주문, 불만/클레임 등 레스토랑 고객 지원에 직접 관련된 내용만 허용합니다.
인사나 짧은 일상 대화(예: 안녕, 안녕하세요, 하이, 오늘 날씨 좋네요)는 허용합니다. 이 경우 is_off_topic은 false로 두세요.

판단 기준:
- is_off_topic: 인사/일상 대화가 아니면서, 날씨 논의·인생 상담·일반 상식·다른 업종 문의 등 레스토랑 고객 지원과 무관한 주제면 true, 관련 있거나 인사/일상 대화면 false.
- is_inappropriate: 욕설, 비방, 성적 표현, 혐오 발언 등 부적절한 내용이 있으면 true, 없으면 false.
- reason: 판단 이유를 한 문장으로 짧게 작성하세요.
""",
    output_type=InputGuardRailOutput,
)

output_guardrail_agent = Agent(
    name="Output Guardrail",
    instructions="""
당신은 봇이 사용자에게 보내기 직전 응답이 기준을 만족하는지 검사하는 검사자입니다.

검사 기준:
1. 전문적이고 정중한 응답인가 (is_proffesional, is_polite)
   - 전문적: 레스토랑 고객 응대에 맞는 말투와 수준의 정보를 제공하는가.
   - 정중함: 존댓말과 공손한 표현을 사용하는가. 무례하거나 과도하게 친근하지 않은가.
2. 내부 정보를 노출하지 않았는가 (is_private_information)
   - 내부 정보: 매출/원가, 직원 개인정보, 내부 정책 세부, 비공개 프로모션 계획 등 고객에게 공개되지 말아야 할 정보. 이에 해당하면 true.

각 필드에 true/false를 정확히 넣고, reason에 판단 이유를 한 문장으로 짧게 작성하세요.
""",
    output_type=OutputGuardRailOutput,
)

@input_guardrail
async def input_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    input: str,
):
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.is_off_topic
        or validation.is_inappropriate
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )


@output_guardrail
async def output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        not validation.is_proffesional
        or not validation.is_polite
        or validation.is_private_information
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )