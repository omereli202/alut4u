from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# A chat message: {"role": "user" | "assistant", "content": str}
Message = dict[str, str]


@dataclass(frozen=True, slots=True)
class StoryPage:
    text: str
    image_prompt: str


@dataclass(frozen=True, slots=True)
class ComposedStory:
    title: str
    protagonist: str
    situation: str
    goal: str
    pages: list[StoryPage]


@dataclass(frozen=True, slots=True)
class ChatTurn:
    reply: str
    ready: bool  # the agent has enough to compose the story
    llm_tokens: int = 0


class StoryAI(Protocol):
    name: str

    def interview(self, messages: list[Message]) -> ChatTurn:
        """Given the conversation so far, produce the agent's next message."""
        ...

    def compose(self, messages: list[Message]) -> ComposedStory:
        """Turn the finished interview into a structured social story."""
        ...

    def illustrate(self, prompt: str, protagonist: str) -> tuple[bytes, str]:
        """Return (image_bytes, mime) for one page."""
        ...


class AIError(RuntimeError):
    pass
