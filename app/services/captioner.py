import base64
from pathlib import Path
from openai import OpenAI
from app.core.config import settings

def _to_data_url(image_path: str) -> str:
    p = Path(image_path)
    mime = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    b64 = base64.b16encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def generate_caption(image_path: str) -> str:
    if not settings.DASHSCOPE_API_KEY:
        return "frame content (no api key configured)"

    client = OpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_API_BASE_URL,
    )

    data_url = _to_data_url(image_path)

    resp = client.chat.completions.create(
        model=settings.VLM_MODEL,
        messages=[
            {"role":"system", "content":"你是视频帧分析助手，请用简短中文描述画面主体、动作、场景和可见文字。"},
            {"role": "user", "content": [
                {"type": "text", "text": "请描述这张视频帧，输出一句话。"},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]}
        ],
        temperature=0.2
    )
    return (resp.choices[0].message.content or "").strip()
