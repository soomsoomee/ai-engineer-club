from google.adk.agents import ParallelAgent, SequentialAgent

from ...callbacks import after_parallel_illustrations, build_page_image_progress_agent

from .page_illustrator_agent import PageIllustratorAgent


def _page_branches() -> list[SequentialAgent]:
    branches = []
    for i in range(1, 6):
        branches.append(
            SequentialAgent(
                name=f"page_{i}_branch",
                description=f"{i}페이지: 이미지 진행 알림(before_model_callback) 후 일러스트 생성",
                sub_agents=[
                    build_page_image_progress_agent(i),
                    PageIllustratorAgent(
                        name=f"illustrator_page_{i}",
                        description=f"{i}페이지 일러스트 생성",
                        page_number=i,
                    ),
                ],
            )
        )
    return branches


parallel_illustrations_agent = ParallelAgent(
    name="parallel_illustrations",
    description=(
        "story_writer_output를 사용해 페이지별 SequentialAgent(진행 콜백 + 일러스트)를 "
        "ParallelAgent로 동시에 실행합니다."
    ),
    sub_agents=_page_branches(),
    after_agent_callback=after_parallel_illustrations,
)
