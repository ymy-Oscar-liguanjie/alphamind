import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()


def _get_api_config():
    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
        or ""
    )

    base_url = (
        os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("API_BASE_URL")
        or os.getenv("ANTHROPIC_BASE_URL")
        or "https://tdyun.ai"
    )

    return api_key, base_url.rstrip("/")


def _get_mime(filename, image_bytes=None):
    """
    优先读取真实图片文件头，避免：
    声明 image/png 实际 image/jpeg
    """

    try:
        if image_bytes:
            # JPEG
            if image_bytes.startswith(b"\xff\xd8\xff"):
                return "image/jpeg"

            # PNG
            if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                return "image/png"

            # WEBP
            if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:20]:
                return "image/webp"

    except Exception:
        pass

    # 兜底：根据扩展名
    ext = filename.lower().split(".")[-1]

    if ext in ["jpg", "jpeg"]:
        return "image/jpeg"

    if ext == "webp":
        return "image/webp"

    return "image/png"


def image_to_text(
    image_bytes,
    filename="image.png",
    prompt="请识别这张图片内容，并给出清晰说明。"
):
    api_key, base_url = _get_api_config()

    if not api_key:
        return "图片识别失败：未配置 API Token，请设置 LLM_API_KEY。"

    model = os.getenv(
        "VISION_MODEL",
        os.getenv("LLM_MODEL", "claude-opus-4-6")
    )

    # 修复 MIME 检测
    mime = _get_mime(filename, image_bytes)

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    image_url = f"data:{mime};base64,{b64}"

    url = f"{base_url}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.3
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        data = resp.json()

        if resp.status_code >= 400:
            return f"图片识别接口错误：{data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"图片识别失败：{str(e)}"


def speech_to_text(audio_file_path):
    api_key, base_url = _get_api_config()

    if not api_key:
        return "语音识别失败：未配置 API Token，请设置 LLM_API_KEY。"

    model = os.getenv("ASR_MODEL", "whisper-1")

    url = f"{base_url}/v1/audio/transcriptions"

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        with open(audio_file_path, "rb") as f:

            resp = requests.post(
                url,
                headers=headers,
                files={
                    "file": f
                },
                data={
                    "model": model,
                    "language": "zh"
                },
                timeout=180
            )

        result = resp.json()

        if resp.status_code >= 400:
            return f"语音识别接口错误：{result}"

        return result.get("text", "")

    except Exception as e:
        return f"语音识别失败：{str(e)}"