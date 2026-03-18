from typing import List

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from .prompt import STORY_WRITER_DESCRIPTION, STORY_WRITER_PROMPT


class PageOutput(BaseModel):
    text: str = Field(description="해당 페이지에 표시할 동화 본문")
    visual: str = Field(description="해당 페이지 일러스트 생성용 시각적 설명")


class StoryOutput(BaseModel):
    title: str = Field(description="동화 제목")
    pages: List[PageOutput] = Field(
        description="5페이지 분량의 동화 데이터 (각 페이지는 text, visual 필드 포함)"
    )

MODEL = LiteLlm(model="openai/gpt-4o")

story_writer_agent = Agent(
    name="story_writer_agent",
    description=STORY_WRITER_DESCRIPTION,
    instruction=STORY_WRITER_PROMPT,
    model=MODEL,
    output_schema=StoryOutput,
    output_key="story_writer_output",
)
