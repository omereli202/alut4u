"""The deterministic story agent — no Supabase, no key, no network."""

from __future__ import annotations

from pathlib import Path

from app.services.ai import stub_story
from app.services.ai.base import SENTENCE_TYPES
from app.services.ai.stub_story import StubStoryAI


def _answers(*vals: str) -> list[dict]:
    msgs: list[dict] = []
    for v in vals:
        msgs.append({"role": "user", "content": v})
        msgs.append({"role": "assistant", "content": "?"})
    return msgs


# situation, schedule, goal, sensory, triggers, extras — no name (it's a kwarg)
_FULL = ("מעבר לגן", "מחר בבוקר", "להיפרד ברוגע", "רגיש לרעש", "אין", "לא")


def test_interview_prefills_name_and_asks_the_closing_question():
    ai = StubStoryAI()
    turn = ai.interview([], protagonist="דני")
    assert turn.ready is False
    assert turn.slots.protagonist == "דני"  # never asked
    assert turn.slots.missing() == ["situation", "schedule", "goal", "sensory", "triggers"]

    # all facts in, but the "anything else?" question not answered yet
    facts = ai.interview(_answers("מעבר לגן", "מחר", "רוגע", "רעש", "אין"), protagonist="דני")
    assert facts.ready is False
    assert not facts.slots.missing()
    assert "נוסף" in facts.reply

    full = ai.interview(_answers(*_FULL), protagonist="דני")
    assert full.ready is True
    assert full.slots.schedule == "מחר בבוקר"


def test_compose_shape_and_carol_gray_types():
    ai = StubStoryAI()
    story = ai.compose(
        _answers("מעבר לגן", "ביום שלישי", "להיפרד ברוגע", "רעש חזק", "אין", "כלב השמור שלו"),
        protagonist="דני",
    )
    assert "דני" in story.title
    assert 4 <= len(story.pages) <= 15
    assert all(p.sentence_type in SENTENCE_TYPES for p in story.pages)
    assert story.review_notes
    assert story.revised is False
    joined = " ".join(p.text for p in story.pages)
    assert "רעש חזק" in joined  # sensory woven in
    assert "כלב השמור שלו" in joined  # the "anything else?" answer woven in
    # timing is present but not forced into the opening line
    assert "ביום שלישי" in joined
    assert "ביום שלישי" not in story.pages[0].text
    assert story.schedule == "ביום שלישי"
    assert story.character_sheet


def test_illustrate_is_deterministic_and_ignores_reference():
    a = StubStoryAI().illustrate("a child pausing", "דני")
    b = StubStoryAI().illustrate(
        "a child pausing",
        "דני",
        character_sheet="tall, red hair",
        reference_image=(b"xyz", "image/png"),
    )
    assert a == b
    assert a[1] == "image/svg+xml"


def test_no_unsalted_hash_regression():
    # hash() on a str is PYTHONHASHSEED-salted; the stub must not seed its art
    # from it or pages of one story get inconsistent art across gunicorn workers.
    src = Path(stub_story.__file__).read_text(encoding="utf-8")
    assert "hash(prompt" not in src
    assert "abs(hash(" not in src
