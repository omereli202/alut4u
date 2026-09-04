"""The Gemini story adapter over a fake transport — no key, no network."""

from __future__ import annotations

import base64
import json

import pytest

from app.config import Settings
from app.services.ai import get_story_ai
from app.services.ai.base import AIError
from app.services.ai.gemini_story import GeminiStoryAI
from app.services.ai.stub_story import StubStoryAI

_KEY = "not-a-real-key-test-only"


def _ai() -> GeminiStoryAI:
    return GeminiStoryAI(Settings(app_env="test", gemini_api_key=_KEY))


def _text_response(obj: dict, *, tokens: int = 100, finish: str = "STOP") -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": json.dumps(obj, ensure_ascii=False)}]},
                "finishReason": finish,
            }
        ],
        "usageMetadata": {"totalTokenCount": tokens},
    }


class _Recorder:
    """Stands in for GeminiStoryAI._post; returns queued responses in order."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, model, method, payload, *, timeout=60.0):
        self.calls.append((model, method, payload))
        return self._responses.pop(0)


def _answers(*vals: str) -> list[dict]:
    msgs: list[dict] = []
    for v in vals:
        msgs.append({"role": "user", "content": v})
        msgs.append({"role": "assistant", "content": "?"})
    return msgs


_DRAFT = {
    "title": "הסיפור של דנה",
    "protagonist": "דנה",
    "situation": "מעבר לגן",
    "goal": "להיכנס ברוגע",
    "pages": [
        {"text": "טקסט 1", "sentence_type": "descriptive"},
        {"text": "טקסט 2", "sentence_type": "perspective"},
        {"text": "טקסט 3", "sentence_type": "directive"},
        {"text": "טקסט 4", "sentence_type": "affirmative"},
    ],
}


def test_interview_parses_slots_and_readiness(monkeypatch):
    ai = _ai()
    rec = _Recorder(
        [
            _text_response(
                {
                    "reply": "מה שם הילד?",
                    "ready": False,
                    "slots": {
                        "protagonist": None,
                        "situation": None,
                        "goal": None,
                        "sensory": None,
                        "triggers": None,
                    },
                },
                tokens=42,
            )
        ]
    )
    monkeypatch.setattr(GeminiStoryAI, "_post", rec)

    turn = ai.interview([])
    assert turn.reply == "מה שם הילד?"
    assert turn.ready is False
    assert turn.slots.missing() == ["protagonist", "situation", "goal", "sensory", "triggers"]
    assert turn.llm_tokens == 42
    # role mapping + structured-output request
    _, method, payload = rec.calls[0]
    assert method == "generateContent"
    assert payload["generationConfig"]["responseMimeType"] == "application/json"


def test_assistant_role_maps_to_model():
    contents = GeminiStoryAI._to_contents(
        [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    )
    assert [c["role"] for c in contents] == ["user", "model"]
    assert contents[1]["parts"][0]["text"] == "b"


def test_compose_makes_three_calls_and_keeps_approved_text(monkeypatch):
    ai = _ai()
    rec = _Recorder(
        [
            _text_response(_DRAFT, tokens=1000),
            _text_response({"approved": True, "notes": ["הערה"], "revised": None}, tokens=200),
            _text_response({"prompts": ["p1", "p2", "p3", "p4"]}, tokens=50),
        ]
    )
    monkeypatch.setattr(GeminiStoryAI, "_post", rec)

    story = ai.compose(_answers("דנה", "מעבר לגן", "רוגע", "רעש", "אין"))
    assert len(rec.calls) == 3
    assert [p.text for p in story.pages] == ["טקסט 1", "טקסט 2", "טקסט 3", "טקסט 4"]
    assert story.pages[0].image_prompt == "p1"
    assert story.revised is False
    assert story.review_notes == ("הערה",)
    assert story.llm_tokens == 1250  # summed across the three calls


def test_compose_revise_branch_replaces_text(monkeypatch):
    ai = _ai()
    revised = {
        "title": "כותרת מתוקנת",
        "pages": [
            {"text": "מתוקן 1", "sentence_type": "descriptive"},
            {"text": "מתוקן 2", "sentence_type": "descriptive"},
            {"text": "מתוקן 3", "sentence_type": "perspective"},
            {"text": "מתוקן 4", "sentence_type": "affirmative"},
        ],
    }
    rec = _Recorder(
        [
            _text_response(_DRAFT),
            _text_response({"approved": False, "notes": ["תוקן"], "revised": revised}),
            _text_response({"prompts": ["a", "b", "c", "d"]}),
        ]
    )
    monkeypatch.setattr(GeminiStoryAI, "_post", rec)

    story = ai.compose(_answers("דנה"))
    assert story.title == "כותרת מתוקנת"
    assert story.pages[0].text == "מתוקן 1"
    assert story.revised is True
    # the illustrator ran on the revised text
    art_payload = rec.calls[2][2]
    assert "מתוקן 1" in art_payload["contents"][0]["parts"][0]["text"]


def test_compose_null_revised_falls_back_without_error(monkeypatch):
    ai = _ai()
    rec = _Recorder(
        [
            _text_response(_DRAFT),
            _text_response({"approved": False, "notes": ["x"], "revised": None}),
            _text_response({"prompts": ["a", "b", "c", "d"]}),
        ]
    )
    monkeypatch.setattr(GeminiStoryAI, "_post", rec)
    story = ai.compose(_answers("דנה"))
    assert story.pages[0].text == "טקסט 1"
    assert story.revised is False


def test_blocked_response_raises_ai_error(monkeypatch):
    ai = _ai()
    monkeypatch.setattr(
        GeminiStoryAI,
        "_post",
        _Recorder([_text_response({"reply": "x", "ready": False, "slots": {}}, finish="SAFETY")]),
    )
    with pytest.raises(AIError):
        ai.interview([])


def test_illustrate_extracts_inline_image(monkeypatch):
    ai = _ai()
    png = b"\x89PNG\r\n\x1a\n fake bytes"
    resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "here is the image"},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(png).decode(),
                            }
                        },
                    ]
                },
                "finishReason": "STOP",
            }
        ]
    }
    monkeypatch.setattr(GeminiStoryAI, "_post", _Recorder([resp]))
    data, mime = ai.illustrate("a child pausing", "דנה")
    assert data == png
    assert mime == "image/png"


def test_illustrate_without_image_raises(monkeypatch):
    ai = _ai()
    resp = {
        "candidates": [{"content": {"parts": [{"text": "no image sorry"}]}, "finishReason": "STOP"}]
    }
    monkeypatch.setattr(GeminiStoryAI, "_post", _Recorder([resp]))
    with pytest.raises(AIError):
        ai.illustrate("x", "דנה")


def test_provider_selection():
    assert isinstance(get_story_ai(Settings(app_env="test", gemini_api_key=_KEY)), GeminiStoryAI)
    assert isinstance(get_story_ai(Settings(app_env="test")), StubStoryAI)
