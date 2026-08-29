"""OpenAI adapter for the social-story agent.

Model ids are configurable (``OPENAI_CHAT_MODEL`` / ``OPENAI_IMAGE_MODEL``) —
confirm the current ids for your account rather than trusting defaults. Not
exercised by the test suite (no key); the stub covers the pipeline.
"""

from __future__ import annotations

import base64
import json

import httpx

from app.config import Settings
from app.services.ai.base import AIError, ChatTurn, ComposedStory, Message, StoryPage

_BASE = "https://api.openai.com/v1"

_SYSTEM = (
    "את/ה עוזר/ת ליצור 'סיפור חברתי' (Social Story) לילד/ה על הרצף האוטיסטי, בעברית. "
    "ראיין/י את המטפל/ת בשאלה אחת בכל פעם כדי לברר: שם הדמות הראשית, המצב/הטריגר, "
    "וההתנהגות הרצויה. שאלה קצרה וברורה אחת בלבד בכל תור. "
    "כשיש לך את שלושת הפרטים, כתוב/כתבי בדיוק: READY"
)

_STORY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "protagonist": {"type": "string"},
        "situation": {"type": "string"},
        "goal": {"type": "string"},
        "pages": {
            "type": "array",
            "minItems": 4,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["text", "image_prompt"],
            },
        },
    },
    "required": ["title", "protagonist", "situation", "goal", "pages"],
}


class OpenAIStoryAI:
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.openai_api_key
        self._chat_model = settings.openai_chat_model
        self._image_model = settings.openai_image_model

    def _post(self, path: str, payload: dict, *, timeout: float = 60.0) -> dict:
        try:
            r = httpx.post(
                _BASE + path,
                headers={"Authorization": f"Bearer {self._key}"},
                json=payload,
                timeout=timeout,
            )
        except httpx.HTTPError as e:
            raise AIError(f"openai request failed: {e}") from e
        if r.status_code >= 400:
            raise AIError(f"openai {r.status_code}: {r.text[:300]}")
        return r.json()

    def interview(self, messages: list[Message]) -> ChatTurn:
        body = {
            "model": self._chat_model,
            "messages": [{"role": "system", "content": _SYSTEM}, *messages],
            "temperature": 0.5,
        }
        data = self._post("/chat/completions", body)
        reply = data["choices"][0]["message"]["content"].strip()
        tokens = int(data.get("usage", {}).get("total_tokens", 0))
        if reply == "READY" or reply.endswith("READY"):
            return ChatTurn(
                reply="תודה! יש לי מספיק מידע כדי ליצור את הסיפור.",
                ready=True,
                llm_tokens=tokens,
            )
        return ChatTurn(reply=reply, ready=False, llm_tokens=tokens)

    def compose(self, messages: list[Message]) -> ComposedStory:
        body = {
            "model": self._chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": "כתוב/כתבי סיפור חברתי מלא בעברית, 5 עמודים, לפי המידע מהשיחה.",
                },
                *messages,
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "social_story", "schema": _STORY_SCHEMA, "strict": True},
            },
        }
        data = self._post("/chat/completions", body)
        parsed = json.loads(data["choices"][0]["message"]["content"])
        return ComposedStory(
            title=parsed["title"],
            protagonist=parsed["protagonist"],
            situation=parsed["situation"],
            goal=parsed["goal"],
            pages=[
                StoryPage(text=p["text"], image_prompt=p["image_prompt"]) for p in parsed["pages"]
            ],
        )

    def illustrate(self, prompt: str, protagonist: str) -> tuple[bytes, str]:
        style = (
            "gentle flat illustration for a children's social story, soft colours, "
            "no text, calm, friendly"
        )
        data = self._post(
            "/images/generations",
            {
                "model": self._image_model,
                "prompt": f"{prompt}. Consistent character named {protagonist}. {style}",
                "size": "1024x1024",
                "n": 1,
            },
            timeout=120.0,
        )
        item = data["data"][0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"]), "image/png"
        img_url = item["url"]
        try:
            img = httpx.get(img_url, timeout=60.0)
        except httpx.HTTPError as e:
            raise AIError(f"image download failed: {e}") from e
        return img.content, img.headers.get("content-type", "image/png")
