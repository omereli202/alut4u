"""AI provider abstraction for the social-story agent.

The app depends only on :class:`StoryAI` and :func:`get_story_ai`. A real OpenAI
adapter is used when ``OPENAI_API_KEY`` is set; otherwise a deterministic stub
runs the same pipeline (interview → structured story → per-page image) so the
feature is fully usable in dev without a key.
"""

from __future__ import annotations

from app.config import Settings, current_settings
from app.services.ai.base import ChatTurn, ComposedStory, StoryAI, StoryPage, StorySlots

__all__ = [
    "ChatTurn",
    "ComposedStory",
    "StoryAI",
    "StoryPage",
    "StorySlots",
    "get_story_ai",
]


def get_story_ai(settings: Settings | None = None) -> StoryAI:
    s = settings or current_settings()
    if s.openai_api_key:
        from app.services.ai.openai_story import OpenAIStoryAI

        return OpenAIStoryAI(s)
    from app.services.ai.stub_story import StubStoryAI

    return StubStoryAI()
