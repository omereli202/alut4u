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


def test_interview_is_slot_driven_and_ready_only_when_full():
    ai = StubStoryAI()
    turn = ai.interview(_answers("דני"))
    assert turn.ready is False
    assert turn.slots.protagonist == "דני"
    assert turn.slots.missing() == ["situation", "goal", "sensory", "triggers"]

    full = ai.interview(_answers("דני", "מעבר לגן", "להיפרד ברוגע", "רגיש לרעש", "אין"))
    assert full.ready is True
    assert not full.slots.missing()


def test_compose_shape_and_carol_gray_types():
    ai = StubStoryAI()
    story = ai.compose(_answers("דני", "מעבר לגן", "להיפרד ברוגע", "רעש חזק", "אין"))
    assert "דני" in story.title
    assert 4 <= len(story.pages) <= 8
    assert all(p.sentence_type in SENTENCE_TYPES for p in story.pages)
    assert story.review_notes
    assert story.revised is False
    # the sensory answer is woven into the text
    assert any("רעש חזק" in p.text for p in story.pages)


def test_illustrate_is_deterministic_across_instances():
    a = StubStoryAI().illustrate("a child pausing", "דני")
    b = StubStoryAI().illustrate("a child pausing", "דני")
    assert a == b
    assert a[1] == "image/svg+xml"


def test_no_unsalted_hash_regression():
    # hash() on a str is PYTHONHASHSEED-salted; the stub must not seed its art
    # from it or pages of one story get inconsistent art across gunicorn workers.
    src = Path(stub_story.__file__).read_text(encoding="utf-8")
    assert "hash(prompt" not in src
    assert "abs(hash(" not in src
