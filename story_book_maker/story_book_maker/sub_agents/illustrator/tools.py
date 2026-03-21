import asyncio
import base64
from io import BytesIO

from openai import OpenAI
from PIL import Image

_client: OpenAI | None = None

_MAX_SIDE_PX = 512


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _shrink_jpeg_bytes(data: bytes) -> bytes:
    with Image.open(BytesIO(data)) as im:
        im = im.convert("RGB")
        w, h = im.size
        longest = max(w, h)
        if longest > _MAX_SIDE_PX:
            scale = _MAX_SIDE_PX / longest
            im = im.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                Image.Resampling.LANCZOS,
            )
        out = BytesIO()
        im.save(out, format="JPEG", quality=82, optimize=True)
        return out.getvalue()


def _generate_jpeg_bytes(visual_prompt: str) -> bytes:
    safe_prompt = (
        "Wholesome children's picture book illustration, non-violent, family-friendly. "
        + visual_prompt.strip()
    )
    image = _get_client().images.generate(
        model="gpt-image-1",
        prompt=safe_prompt,
        n=1,
        moderation="low",
        quality="low",
        output_format="jpeg",
        background="opaque",
        size="1024x1024",
    )
    raw = base64.b64decode(image.data[0].b64_json)
    return _shrink_jpeg_bytes(raw)


async def fetch_page_jpeg_bytes(visual_prompt: str) -> bytes:
    return await asyncio.to_thread(_generate_jpeg_bytes, visual_prompt)
