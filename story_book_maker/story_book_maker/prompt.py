STORY_BOOK_PIPELINE_DESCRIPTION = (
    "SequentialAgent: story_writing_progress(LlmAgent, before_model_callback) → StoryWriterAgent → "
    "ParallelAgent(페이지별 Sequential: 이미지 진행 before_model_callback → PageIllustratorAgent). "
    "스토리는 Agent State에, 이미지는 Artifacts에 저장하고 after_parallel_illustrations 콜백으로 동화책을 정리합니다."
)
