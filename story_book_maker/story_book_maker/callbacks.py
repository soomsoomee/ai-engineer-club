import base64
from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

_PROGRESS_LLM = LiteLlm(model="openai/gpt-4o-mini")


def _part_to_data_uri_markdown(part: types.Part | None) -> str | None:
    if part is None or part.inline_data is None or not part.inline_data.data:
        return None
    mime = part.inline_data.mime_type or "image/jpeg"
    b64 = base64.standard_b64encode(part.inline_data.data).decode("ascii")
    return f"![](data:{mime};base64,{b64})"


def before_model_story_progress(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse:
    del callback_context, llm_request
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text="스토리 작성 중...")],
        ),
        finish_reason=types.FinishReason.STOP,
    )


def build_story_writing_progress_agent() -> Agent:
    return Agent(
        name="story_writing_progress",
        description="before_model_callback으로 스토리 작성 진행 문구만 출력합니다.",
        instruction=".",
        model=_PROGRESS_LLM,
        before_model_callback=before_model_story_progress,
    )


def _before_model_page_image_progress(page_number: int):
    def before_model_page_image_progress(
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> LlmResponse:
        del callback_context, llm_request
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(text=f"이미지 {page_number}/5 생성 중..."),
                ],
            ),
            finish_reason=types.FinishReason.STOP,
        )

    return before_model_page_image_progress


def build_page_image_progress_agent(page_number: int) -> Agent:
    return Agent(
        name=f"page_{page_number}_image_progress",
        description="before_model_callback으로 해당 페이지 일러스트 진행 문구만 출력합니다.",
        instruction=".",
        model=_PROGRESS_LLM,
        before_model_callback=_before_model_page_image_progress(page_number),
    )


async def after_parallel_illustrations(callback_context: CallbackContext) -> Optional[types.Content]:
    story = callback_context.state.get("story_writer_output")
    if not story:
        return types.Content(
            role="model",
            parts=[types.Part(text="동화 데이터가 없어 최종 책을 만들 수 없습니다.")],
        )

    title = story.get("title", "")
    pages = story.get("pages", [])
    artifact_keys = await callback_context.list_artifacts()

    body_parts: list[str] = [
        f"**제목:** {title}\n",
        "\n---\n",
    ]

    result_pages = []
    for i, page in enumerate(pages, start=1):
        text = page.get("text", "")
        fn = f"page_{i}_image.jpeg"
        image_ok = False
        image_line = ""

        if fn in artifact_keys:
            loaded = await callback_context.load_artifact(fn)
            md = _part_to_data_uri_markdown(loaded)
            if md:
                image_line = md
                image_ok = True
            elif loaded is not None:
                image_line = f"_(페이지 {i}: 이미지 바이너리를 표시할 수 없습니다.)_"
            else:
                image_line = f"_(페이지 {i}: 이미지 불러오기 실패)_"
        else:
            image_line = f"_(페이지 {i}: 이미지 없음)_"

        body_parts.append(f"\n**{i}페이지**\n\n{image_line}\n\n{text}\n")
        if i < len(pages):
            body_parts.append("\n---\n")

        result_pages.append({
            "page": i,
            "text": text,
            "visual": page.get("visual", ""),
            "image": f"[Artifact: {fn}]" if image_ok else "",
        })

    callback_context.state["illustrator_output"] = {
        "title": title,
        "pages": result_pages,
        "status": "completed",
    }

    return types.Content(
        role="model",
        parts=[types.Part(text="".join(body_parts))],
    )
