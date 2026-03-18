from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from .prompt import STORY_BOOK_MAKER_PROMPT, STORY_BOOK_MAKER_DESCRIPTION
from .sub_agents.story_writer.agent import story_writer_agent
from .sub_agents.illustrator.agent import illustrator_agent


MODEL = LiteLlm(model="openai/gpt-4o")

story_book_maker_agent = Agent(
    name="story_book_maker_agent",
    description=STORY_BOOK_MAKER_DESCRIPTION,
    instruction=STORY_BOOK_MAKER_PROMPT,
    model=MODEL,
    tools=[
        AgentTool(agent=story_writer_agent),
        AgentTool(agent=illustrator_agent),
    ],
)

root_agent = story_book_maker_agent