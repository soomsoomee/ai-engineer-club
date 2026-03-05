import streamlit as st
from openai import OpenAI
from agents import (
    Agent,
    Runner,
    SQLiteSession,
    WebSearchTool,
    FileSearchTool,
    ImageGenerationTool,
)
import asyncio
import dotenv
import os
import base64

dotenv.load_dotenv()
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
client = OpenAI()

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history", 
        "life-coach-memory.db")
session = st.session_state["session"]


def get_event_type(data):
    if hasattr(data, "type"):
        return data.type
    if isinstance(data, dict):
        return data.get("type")
    return None


def update_status(status_container, event_type: str):
    status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": ("🔎 Starting web search...", "running"),
        "response.web_search_call.searching": ("🔎 Web search in progress...", "running"),
        "response.file_search_call.completed": ("✅ File search completed.", "complete"),
        "response.file_search_call.in_progress": ("📂 Starting file search...", "running"),
        "response.file_search_call.searching": ("📂 File search in progress...", "running"),
        "response.image_generation_call.generating": ("🎨 Generating image...", "running"),
        "response.image_generation_call.completed": ("✅ Image generated.", "complete"),
        "response.image_generation_call.in_progress": ("🎨 Starting image generation...", "running"),
        "response.completed": ("", "complete"),
    }
    if event_type in status_messages:
        label, state = status_messages[event_type]
        status_container.update(label=label, state=state)


async def run_agent(message):
    agent = Agent(
        name = "Life Coach",
        instructions = """
당신은 전문적인 라이프 코치입니다. 사용자의 개인적 성장과 목표 달성을 돕는 것이 주요 역할입니다.

핵심 역할:
1. 동기부여: 사용자가 목표를 향해 나아갈 수 있도록 격려하고 동기를 부여합니다
2. 자기개발 조언: 개인의 강점을 발견하고 약점을 개선할 수 있는 구체적인 방법을 제시합니다
3. 습관 형성 지원: 좋은 습관을 만들고 나쁜 습관을 고치는 실용적인 전략을 제공합니다

웹 검색 활용 원칙:
- 사용자의 질문이나 고민에 대해 답변할 때는 최대한 관련 웹 검색을 먼저 수행합니다
- 최신 연구 결과, 전문가 조언, 실용적인 팁을 찾기 위해 적극적으로 검색합니다
- 검색 키워드는 구체적이고 한국어로 작성합니다
- 예시: "아침 일찍 일어나는 방법", "습관 만들기 과학적 방법", "동기부여 심리학 연구"

파일 검색 활용 원칙:
- 사용자의 개인적인 질문이나 고민에 대해 답변할 때는 최대한 관련 파일을 검색합니다

이미지 생성 활용 원칙:
- 사용자가 이미지 제작을 원하면 ImageGenerationTool을 적극적으로 사용합니다
- 아래 유형의 이미지를 요청하면 구체적인 구성 요소를 확인한 뒤 생성합니다
- 목표 기반 비전 보드: 핵심 목표, 마감 시점, 실천 항목이 한눈에 보이게 구성합니다
- 맞춤 메시지가 담긴 동기부여 포스터: 사용자의 상황에 맞는 짧고 강한 문구를 포함합니다
- 진행 상황의 시각적 표현: 단계, 퍼센트, 마일스톤을 쉽게 이해할 수 있는 형태로 표현합니다
- 이미지를 생성할 때는 사용자가 원하는 톤, 색감, 텍스트 포함 여부를 먼저 확인합니다

대화 스타일:
- 따뜻하고 공감적인 톤으로 대화합니다
- 웹 검색으로 찾은 최신 정보와 과학적 근거를 바탕으로 조언합니다
- 구체적이고 실행 가능한 조언을 제공합니다
- 사용자의 상황과 감정을 깊이 이해하려 노력합니다
- 작은 성취도 인정하고 격려합니다

항상 한국어로 답변하며, 사용자가 스스로 답을 찾아갈 수 있도록 질문을 통해 생각을 유도합니다.
        """,
        tools = [
            WebSearchTool(),
            FileSearchTool(
                    vector_store_ids=[VECTOR_STORE_ID],
                    max_num_results=3
                ),
                ImageGenerationTool(
                    tool_config={
                        "type": "image_generation",
                        "quality": "high",
                        "output_format": "jpeg",
                        "moderation": "low",
                        "partial_images": 1
                    }
                ),
        ],
    )

    with st.chat_message("ai"): 
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        image_placeholder = st.empty()
        st.session_state["text_placeholder"] = text_placeholder
        response = ""

        stream = Runner.run_streamed(
                agent, 
                message, 
                session=session)

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                event_type = get_event_type(event.data)
                if event_type:
                    update_status(status_container, event_type)
                if event_type == "response.output_text.delta":
                    response += getattr(event.data, "delta", "") or event.data.get("delta", "")
                    text_placeholder.write(response.replace("$", "\\$"))
                elif event_type == "response.image_generation_call.partial_image":
                        image_b64 = getattr(event.data, "partial_image_b64", None) or event.data.get("partial_image_b64")
                        if image_b64:
                            image_placeholder.image(base64.b64decode(image_b64))


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    content = message["content"]
                    if isinstance(content, str):
                        st.write(content)
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))
        if "type" in message:
            message_type = message["type"]
            if message_type == "web_search_call":
                with st.chat_message("ai"):
                    st.write(f"🔎 다음 키워드에 대해 검색: {message['action']['query']}")
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write(f"📂 Searched your files for [{message['queries'][0]}]...")
            elif message_type == "image_generation_call":
                with st.chat_message("ai"):
                    image = base64.b64decode(message["result"])
                    st.image(image)

asyncio.run(paint_history())

prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=[
        "txt"
        ]
    )

if prompt:

    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("📄 Uploading file...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()),
                        purpose="user_data"
                    )
                    status.update(label="📄 Attaching file...")
                    client.vector_stores.files.create(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=uploaded_file.id
                    )
                    status.update(label="📄 File uploaded.", state="complete")

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
