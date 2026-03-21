from google.adk.agents import SequentialAgent

from .callbacks import build_story_writing_progress_agent
from .prompt import STORY_BOOK_PIPELINE_DESCRIPTION
from .sub_agents.illustrator.parallel_illustrations import parallel_illustrations_agent
from .sub_agents.story_writer.agent import story_writer_agent

root_agent = SequentialAgent(
    name="story_book_pipeline",
    description=STORY_BOOK_PIPELINE_DESCRIPTION,
    sub_agents=[
        build_story_writing_progress_agent(),
        story_writer_agent,
        parallel_illustrations_agent,
    ],
)
