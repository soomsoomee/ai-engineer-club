import base64

from google.adk.tools.tool_context import ToolContext
from google.genai import types
from openai import OpenAI

client = OpenAI()


async def generate_images(tool_context: ToolContext):
    story_writer_output = tool_context.state.get("story_writer_output")
    if not story_writer_output:
        return {"pages": [], "error": "story_writer_output가 State에 없습니다. StoryWriterAgent를 먼저 실행하세요."}

    pages = story_writer_output.get("pages", [])
    existing_artifacts = await tool_context.list_artifacts()
    result_pages = []

    for page_idx, page in enumerate(pages):
        text = page.get("text", "")
        visual = page.get("visual", "")
        filename = f"page_{page_idx + 1}_image.jpeg"

        if filename in existing_artifacts:
            result_pages.append({
                "page": page_idx + 1,
                "text": text,
                "visual": visual,
                "image": f"[생성된 이미지가 Artifact로 저장됨: {filename}]",
            })
            continue

        image = client.images.generate(
            model="gpt-image-1",
            prompt=visual,
            n=1,
            moderation="low",
            quality="low",
            output_format="jpeg",
            background="opaque",
            size="1024x1536",
        )

        image_bytes = base64.b64decode(image.data[0].b64_json)
        artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_bytes,
            )
        )

        await tool_context.save_artifact(filename=filename, artifact=artifact)

        result_pages.append({
            "page": page_idx + 1,
            "text": text,
            "visual": visual,
            "image": f"[생성된 이미지가 Artifact로 저장됨: {filename}]",
        })

    return {
        "title": story_writer_output.get("title", ""),
        "pages": result_pages,
        "status": "completed",
    }