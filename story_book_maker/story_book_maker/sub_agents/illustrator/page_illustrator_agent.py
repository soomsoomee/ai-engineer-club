from typing import AsyncGenerator

from openai import APIError, BadRequestError

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.context import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import Field
from typing_extensions import override

from .tools import fetch_page_jpeg_bytes


class PageIllustratorAgent(BaseAgent):
    page_number: int = Field(ge=1, le=5)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        actions = EventActions()
        cx = Context(invocation_context=ctx, event_actions=actions)

        story = cx.state.get("story_writer_output")
        if not story:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text="story_writer_output가 없습니다. StoryWriterAgent를 먼저 실행하세요.",
                        )
                    ],
                ),
                actions=actions,
            )
            return

        pages = story.get("pages", [])
        idx = self.page_number - 1
        if idx < 0 or idx >= len(pages):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"{self.page_number}페이지 데이터가 없습니다.")],
                ),
                actions=actions,
            )
            return

        page = pages[idx]
        text = page.get("text", "")
        visual = page.get("visual", "")
        filename = f"page_{self.page_number}_image.jpeg"

        existing = await cx.list_artifacts()
        if filename not in existing:
            try:
                image_bytes = await fetch_page_jpeg_bytes(visual)
            except BadRequestError as err:
                detail = ""
                body = getattr(err, "body", None)
                if isinstance(body, dict):
                    inner = body.get("error")
                    if isinstance(inner, dict) and inner.get("code") == "moderation_blocked":
                        detail = " (안전 정책에 의해 차단됨)"
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=(
                                    f"이미지 {self.page_number}/5 생성 실패{detail}. "
                                    "다른 페이지는 계속 진행합니다."
                                ),
                            )
                        ],
                    ),
                    actions=actions,
                )
                return
            except APIError as err:
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=(
                                    f"이미지 {self.page_number}/5 API 오류: {err!s}"
                                ),
                            )
                        ],
                    ),
                    actions=actions,
                )
                return
            except Exception as err:
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=(
                                    f"이미지 {self.page_number}/5 생성 실패: {err!s}"
                                ),
                            )
                        ],
                    ),
                    actions=actions,
                )
                return

            artifact = types.Part(
                inline_data=types.Blob(
                    mime_type="image/jpeg",
                    data=image_bytes,
                )
            )
            await cx.save_artifact(filename=filename, artifact=artifact)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=(
                            f"이미지 {self.page_number}/5 생성 완료 "
                            f"(저장: {filename})"
                        ),
                    )
                ],
            ),
            actions=actions,
        )
