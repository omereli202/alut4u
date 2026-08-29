"""Deterministic social-story agent for dev / CI (no OpenAI key).

Runs the real shape of the flow: a 3-question interview, a templated 5-page
Hebrew social story, and a simple SVG illustration per page.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from app.services.ai.base import ChatTurn, ComposedStory, Message, StoryPage

_QUESTIONS = [
    "מה שם הילד או הילדה שהסיפור מספר עליהם?",
    "באיזה מצב הסיפור אמור לעזור? (למשל: מעבר לגן, ביקור אצל הרופא, פרידה מההורים)",
    "מה ההתנהגות הרצויה שנרצה לחזק בסיפור?",
]

_PAGE_EMOJI = ["🌅", "🤔", "🫁", "🙂", "⭐"]


class StubStoryAI:
    name = "stub"

    def interview(self, messages: list[Message]) -> ChatTurn:
        answered = sum(1 for m in messages if m["role"] == "user")
        if answered < len(_QUESTIONS):
            return ChatTurn(reply=_QUESTIONS[answered], ready=False)
        return ChatTurn(
            reply="תודה! יש לי מספיק מידע כדי ליצור את הסיפור. אפשר להמשיך.",
            ready=True,
        )

    def compose(self, messages: list[Message]) -> ComposedStory:
        answers = [m["content"].strip() for m in messages if m["role"] == "user"]
        protagonist = answers[0] if answers else "הילד"
        situation = answers[1] if len(answers) > 1 else "מצב חדש"
        goal = answers[2] if len(answers) > 2 else "להישאר רגוע"

        pages = [
            StoryPage(
                text=(
                    f"לפעמים {protagonist} מגיע/ה למצב חדש: {situation}. "
                    "זה בסדר להרגיש קצת לא בטוח/ה."
                ),
                image_prompt=f"{protagonist} at the start of {situation}, calm illustration",
            ),
            StoryPage(
                text=f"כש{protagonist} מרגיש/ה לא נעים, אפשר לעצור רגע ולשים לב לגוף.",
                image_prompt=f"{protagonist} pausing and noticing feelings",
            ),
            StoryPage(
                text=f"{protagonist} יכול/ה לנשום לאט: שאיפה ארוכה, ואז נשיפה ארוכה.",
                image_prompt=f"{protagonist} taking a slow breath",
            ),
            StoryPage(
                text=f"אחרי כמה נשימות {protagonist} מרגיש/ה קצת יותר רגוע/ה, ומנסה {goal}.",
                image_prompt=f"{protagonist} trying to {goal}, hopeful",
            ),
            StoryPage(
                text=f"{protagonist} עשה/עשתה עבודה נהדרת! גם אם היה קשה, {protagonist} התמודד/ה.",
                image_prompt=f"{protagonist} succeeding, proud and happy",
            ),
        ]
        return ComposedStory(
            title=f"הסיפור של {protagonist}: {situation}",
            protagonist=protagonist,
            situation=situation,
            goal=goal,
            pages=pages,
        )

    def illustrate(self, prompt: str, protagonist: str) -> tuple[bytes, str]:
        idx = abs(hash(prompt)) % len(_PAGE_EMOJI)
        hue = (abs(hash(prompt)) % 8) * 40
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            f'<rect width="400" height="300" fill="hsl({hue} 55% 88%)"/>'
            f'<text x="200" y="150" font-size="90" text-anchor="middle" '
            f'dominant-baseline="central">{_PAGE_EMOJI[idx]}</text>'
            f'<text x="200" y="250" font-size="22" text-anchor="middle" '
            f'fill="hsl({hue} 40% 35%)">{escape(protagonist)}</text></svg>'
        )
        return svg.encode("utf-8"), "image/svg+xml"
