"""Deterministic social-story agent for dev / CI (no Gemini key).

Runs the real shape of the four-role pipeline: a slot-driven interview
(protagonist / situation / schedule / goal / sensory sensitivities / triggers), a
templated Hebrew social story with Carol Gray sentence types, a character sheet,
per-page visual prompts, a canned clinical review, and a simple SVG illustration
per page.
"""

from __future__ import annotations

import hashlib
from xml.sax.saxutils import escape

from app.services.ai.base import (
    ChatTurn,
    ComposedStory,
    Message,
    StoryPage,
    StorySlots,
)

# Slot name -> the question the interviewer asks when that slot is still empty.
_QUESTIONS: list[tuple[str, str]] = [
    ("protagonist", "מה שם הילד או הילדה שהסיפור מספר עליהם?"),
    (
        "situation",
        "באיזה מצב הסיפור אמור לעזור? (למשל: מעבר לגן, ביקור אצל הרופא, פרידה מההורים)",
    ),
    (
        "schedule",
        "מתי האירוע צפוי לקרות? (למשל: מחר בבוקר, ביום שלישי הקרוב, בשבוע הבא)",
    ),
    ("goal", "מה ההתנהגות הרצויה שנרצה לחזק בסיפור?"),
    (
        "sensory",
        'האם יש רגישויות חושיות שכדאי להתחשב בהן? (רעש, אור, מגע, ריח) אם אין — כתבו "אין".',
    ),
    (
        "triggers",
        'האם יש טריגרים ידועים שמקשים על הילד/ה במצב הזה? אם אין — כתבו "אין".',
    ),
]

_PAGE_EMOJI = ["🌅", "🤔", "🫁", "🙂", "⭐"]


def _slots_from_messages(messages: list[Message]) -> StorySlots:
    """Assign user answers to slots positionally, in question order."""
    answers = [m["content"].strip() for m in messages if m.get("role") == "user"]
    names = [name for name, _ in _QUESTIONS]
    filled = dict(zip(names, answers, strict=False))
    return StorySlots.from_dict(filled)


class StubStoryAI:
    name = "stub"

    def interview(self, messages: list[Message]) -> ChatTurn:
        slots = _slots_from_messages(messages)
        missing = slots.missing()
        if missing:
            question = next(q for name, q in _QUESTIONS if name == missing[0])
            return ChatTurn(reply=question, ready=False, slots=slots)
        return ChatTurn(
            reply="תודה! יש לי מספיק מידע כדי ליצור את הסיפור. אפשר להמשיך.",
            ready=True,
            slots=slots,
        )

    def compose(self, messages: list[Message]) -> ComposedStory:
        slots = _slots_from_messages(messages)
        protagonist = slots.protagonist or "הילד"
        situation = slots.situation or "מצב חדש"
        goal = slots.goal or "להישאר רגוע"
        sensory = (slots.sensory or "").strip()
        triggers = (slots.triggers or "").strip()
        schedule = (slots.schedule or "").strip()

        has_sensory = bool(sensory) and sensory not in {"אין", "לא", "-"}
        has_triggers = bool(triggers) and triggers not in {"אין", "לא", "-"}
        when = schedule if schedule and schedule not in {"אין", "לא", "-"} else "בקרוב"

        page3_text = f"{protagonist} יכול/ה לנשום לאט: שאיפה ארוכה, ואז נשיפה ארוכה."
        if has_sensory:
            page3_text += f" לפעמים {sensory} מרגיש/ה חזק, וגם אז הנשימה עוזרת."

        page1_text = (
            f"{when} {protagonist} מגיע/ה למצב חדש: {situation}. "
            "בדרך כלל זה בסדר להרגיש קצת לא בטוח/ה."
        )
        if has_triggers:
            page1_text += f" יכול להיות ש{triggers} מקשה קצת, וזה מובן."

        pages = [
            StoryPage(
                text=page1_text,
                image_prompt=(
                    f"{protagonist} at the start of {situation}, calm, one clear expression, "
                    "plain background"
                ),
                sentence_type="descriptive",
            ),
            StoryPage(
                text=f"כש{protagonist} מרגיש/ה לא נעים, אפשר לעצור רגע ולשים לב לגוף.",
                image_prompt=f"{protagonist} pausing and noticing feelings, plain background",
                sentence_type="perspective",
            ),
            StoryPage(
                text=page3_text,
                image_prompt=f"{protagonist} taking a slow breath, calm colours",
                sentence_type="directive",
            ),
            StoryPage(
                text=f"אחרי כמה נשימות {protagonist} מרגיש/ה קצת יותר רגוע/ה, ומנסה {goal}.",
                image_prompt=f"{protagonist} trying to {goal}, hopeful, plain background",
                sentence_type="directive",
            ),
            StoryPage(
                text=(
                    f"{protagonist} עשה/עשתה עבודה נהדרת! גם אם היה קשה, {protagonist} התמודד/ה."
                ),
                image_prompt=f"{protagonist} succeeding, proud and happy, plain background",
                sentence_type="affirmative",
            ),
        ]
        notes = [
            "הסיפור מנוסח בשפה חיובית ובזמן הווה, בהתאם לעקרונות הסיפור החברתי.",
            "יחס המשפטים נשמר: רוב המשפטים תיאוריים או של פרספקטיבה.",
        ]
        if has_sensory or has_triggers:
            notes.append("הרגישויות והטריגרים שנמסרו שולבו בעדינות בטקסט.")
        return ComposedStory(
            title=f"הסיפור של {protagonist}: {situation}",
            protagonist=protagonist,
            situation=situation,
            goal=goal,
            pages=pages,
            schedule=when,
            character_sheet=(
                f"A young child named {protagonist}, short dark hair, wearing a "
                "green t-shirt and blue trousers, light-brown skin, always carrying "
                "a small yellow backpack."
            ),
            review_notes=tuple(notes),
            revised=False,
            llm_tokens=0,
        )

    def illustrate(
        self,
        prompt: str,
        protagonist: str,
        *,
        character_sheet: str = "",
        reference_image: tuple[bytes, str] | None = None,
    ) -> tuple[bytes, str]:
        # character_sheet / reference_image are ignored on purpose — the stub must
        # stay byte-for-byte deterministic (no hashing of the reference bytes).
        # blake2b, not hash(): str hashing is salted per process, so hash() would
        # make this "deterministic" stub pick different art on every restart.
        seed = int.from_bytes(hashlib.blake2b(prompt.encode("utf-8"), digest_size=8).digest())
        idx = seed % len(_PAGE_EMOJI)
        hue = (seed % 8) * 40
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            f'<rect width="400" height="300" fill="hsl({hue} 55% 88%)"/>'
            f'<text x="200" y="150" font-size="90" text-anchor="middle" '
            f'dominant-baseline="central">{_PAGE_EMOJI[idx]}</text>'
            f'<text x="200" y="250" font-size="22" text-anchor="middle" '
            f'fill="hsl({hue} 40% 35%)">{escape(protagonist)}</text></svg>'
        )
        return svg.encode("utf-8"), "image/svg+xml"
