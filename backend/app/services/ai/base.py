from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Protocol

# A chat message: {"role": "user" | "assistant", "content": str}
Message = dict[str, str]

# Carol Gray sentence types the writer tags each page with.
SENTENCE_TYPES = ("descriptive", "perspective", "directive", "affirmative")


@dataclass(frozen=True, slots=True)
class StorySlots:
    """The facts the interviewer agent collects before a story can be composed."""

    protagonist: str | None = None
    situation: str | None = None
    schedule: str | None = None  # when the event happens
    goal: str | None = None
    sensory: str | None = None
    triggers: str | None = None

    def missing(self) -> list[str]:
        return [f.name for f in fields(self) if not getattr(self, f.name)]

    def as_dict(self) -> dict[str, str | None]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict | None) -> StorySlots:
        data = data or {}
        allowed = {f.name for f in fields(cls)}
        clean = {
            k: (v.strip() or None) if isinstance(v, str) else None
            for k, v in data.items()
            if k in allowed
        }
        return cls(**clean)


@dataclass(frozen=True, slots=True)
class StoryPage:
    text: str
    image_prompt: str
    sentence_type: str = "descriptive"


@dataclass(frozen=True, slots=True)
class ComposedStory:
    title: str
    protagonist: str
    situation: str
    goal: str
    pages: list[StoryPage]
    schedule: str = ""
    character_sheet: str = ""  # one description of the protagonist, reused per page
    review_notes: tuple[str, ...] = ()
    revised: bool = False
    llm_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ChatTurn:
    reply: str
    ready: bool  # the agent has enough to compose the story
    slots: StorySlots = field(default_factory=StorySlots)
    llm_tokens: int = 0


class StoryAI(Protocol):
    name: str

    def interview(self, messages: list[Message]) -> ChatTurn:
        """Given the conversation so far, produce the agent's next message."""
        ...

    def compose(self, messages: list[Message]) -> ComposedStory:
        """Turn the finished interview into a structured, reviewed social story."""
        ...

    def illustrate(
        self,
        prompt: str,
        protagonist: str,
        *,
        character_sheet: str = "",
        reference_image: tuple[bytes, str] | None = None,
    ) -> tuple[bytes, str]:
        """Return (image_bytes, mime) for one page. ``reference_image`` is
        ``(bytes, mime)`` of an already-drawn page, used to keep the same
        character across the story."""
        ...


class AIError(RuntimeError):
    pass
