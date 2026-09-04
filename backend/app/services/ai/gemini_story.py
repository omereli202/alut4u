"""Google Gemini adapter for the social-story agent crew.

Four Hebrew roles, each a structured-output ``generateContent`` call:

1. interviewer  — collects five slots, reports readiness as a real field
2. writer       — Carol Gray social story, one sentence-type tag per page
3. reviewer     — senior SLP QA; approves or returns a corrected story, once
4. illustrator  — one visual prompt per (reviewed) page

``compose()`` chains writer → reviewer → illustrator so the art prompts are
built from the final text. Page images come from ``gemini-2.5-flash-image``
("Nano Banana"). Model ids are configurable (``GEMINI_CHAT_MODEL`` /
``GEMINI_IMAGE_MODEL``) — confirm the current ids for your account. Not
exercised by the integration suite (no key); the stub covers the pipeline shape
and ``tests/test_ai_story_gemini.py`` covers this adapter over a fake transport.
"""

from __future__ import annotations

import base64
import json

import httpx

from app.config import Settings
from app.services.ai.base import (
    SENTENCE_TYPES,
    AIError,
    ChatTurn,
    ComposedStory,
    Message,
    StoryPage,
    StorySlots,
)

_GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta"

_BLOCKED_FINISH = {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST"}

# --- Role 1: interviewer -----------------------------------------------------

_INTERVIEW_SYSTEM = (
    "את/ה סוכן/ת מראיין/ת המסייע/ת למטפל/ת לאסוף מידע לסיפור חברתי בעברית. "
    "שאל/י שאלה קצרה, חמה וברורה אחת בכל תור. אם תשובה עמומה — בקש/י הבהרה לפני שתמשיך/י. "
    "עלייך למלא חמישה שדות: שם הדמות (protagonist), המצב או הטריגר (situation), "
    "ההתנהגות הרצויה (goal), רגישויות חושיות (sensory), וטריגרים ידועים (triggers). "
    "החזר/י בכל תור את מצב השדות שמילאת עד כה (ערך null לשדה שעדיין חסר), "
    "וסמן/י ready=true רק כשכל חמשת השדות מלאים. "
    "בשדה reply כתוב/כתבי את השאלה הבאה, או משפט סיום קצר כשסיימת."
)

_SLOT_NAMES = list(StorySlots().as_dict())
_INTERVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "ready": {"type": "boolean"},
        "slots": {
            "type": "object",
            "properties": {n: {"type": "string", "nullable": True} for n in _SLOT_NAMES},
            "required": _SLOT_NAMES,
            "propertyOrdering": _SLOT_NAMES,
        },
    },
    "required": ["reply", "ready", "slots"],
    "propertyOrdering": ["reply", "ready", "slots"],
}

# --- Role 2: writer (Carol Gray) ------------------------------------------

_WRITER_SYSTEM = (
    "את/ה מומחה/ית בכיר/ה לסיפורים חברתיים לפי העקרונות של קרול גריי (Carol Gray), "
    "עם ניסיון רב בכתיבה לילדים על הרצף האוטיסטי. כתוב/כתבי סיפור חברתי בעברית פשוטה "
    "על סמך השיחה שלהלן.\n"
    "כללים מחייבים:\n"
    "1. שפה חיובית ותיאורית — מה כן קורה ומה כן עושים; לעולם לא 'אסור' או 'אל'.\n"
    "2. יחס משפטים: על כל משפט הכוונה (directive) יהיו לפחות שני משפטי תיאור "
    "(descriptive) או פרספקטיבה (perspective).\n"
    "3. פירוק המצב לצעדים קטנים, ברורים ורצופים, בזמן הווה.\n"
    "4. ללא שיפוטיות וללא הבטחות מוחלטות — 'בדרך כלל', 'לפעמים', ולא 'תמיד'.\n"
    "5. התחשבות ברגישויות החושיות ובטריגרים שנמסרו בשיחה.\n"
    "6. 4 עד 8 עמודים, משפט אחד או שניים בעמוד, ללא אימוג'ים.\n"
    "לכל עמוד ציין/י sentence_type — סוג המשפט הדומיננטי בעמוד."
)

_PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "sentence_type": {"type": "string", "enum": list(SENTENCE_TYPES)},
    },
    "required": ["text", "sentence_type"],
    "propertyOrdering": ["text", "sentence_type"],
}
_STORY_BODY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "protagonist": {"type": "string"},
        "situation": {"type": "string"},
        "goal": {"type": "string"},
        "pages": {"type": "array", "minItems": 4, "maxItems": 8, "items": _PAGE_SCHEMA},
    },
    "required": ["title", "protagonist", "situation", "goal", "pages"],
    "propertyOrdering": ["title", "protagonist", "situation", "goal", "pages"],
}

# --- Role 3: reviewer (SLP QA, one bounded round) ------------------------

_REVIEWER_SYSTEM = (
    "את/ה קלינאי/ת תקשורת בכיר/ה עם 20 שנות ניסיון עם ילדים על הרצף האוטיסטי. "
    "קיבלת טיוטת סיפור חברתי ואת תמליל השיחה. בצע/י בקרת איכות אחת.\n"
    "בדוק/בדקי: (א) עמידה בכללי הסיפור החברתי ויחס המשפטים; (ב) ניסוח חיובי ולא שיפוטי; "
    "(ג) האם הסיפור באמת פותר את הקושי שעלה בשיחה; (ד) שפה קונקרטית ללא מטאפורות.\n"
    "אם נדרש תיקון — החזר/י approved=false ואת הסיפור המתוקן המלא בשדה revised "
    "(אותו מספר עמודים או פחות). אם התוצר תקין — approved=true ו-revised=null. "
    "זהו סבב תיקון יחיד. בכל מקרה ספק/י בין הערת סיכום מקצועית אחת לחמש בעברית, "
    "המנוסחות למטפל/ת — מה נבדק או תוקן ואיך כדאי להקריא את הסיפור."
)

_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "notes": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
        "revised": {
            "type": "object",
            "nullable": True,
            "properties": {
                "title": {"type": "string"},
                "pages": {"type": "array", "minItems": 4, "maxItems": 8, "items": _PAGE_SCHEMA},
            },
            "required": ["title", "pages"],
            "propertyOrdering": ["title", "pages"],
        },
    },
    "required": ["approved", "notes", "revised"],
    "propertyOrdering": ["approved", "notes", "revised"],
}

# --- Role 4: illustrator ------------------------------------------------

_ILLUSTRATOR_SYSTEM = (
    "את/ה מאייר/ת המתמחה בהנגשה חזותית לאנשים עם אוטיזם. קיבלת סיפור חברתי סופי. "
    "הפק/י תיאור איור אחד (באנגלית) לכל עמוד, לפי הסדר ובאותו מספר עמודים.\n"
    "כל איור: דמות אחת או שתיים, רקע נקי ופשוט, ללא פרטים מיותרים, הבעת פנים אחת ברורה, "
    "ללא טקסט בתמונה, ועקביות מלאה במראה הדמות לאורך הסיפור. "
    "הימנע/י מגירויים חזותיים עמוסים ומצבעים צורמים, ואל תמחיש/י טריגר בצורה מאיימת."
)


def _illustrator_schema(n: int) -> dict:
    return {
        "type": "object",
        "properties": {
            "prompts": {
                "type": "array",
                "minItems": n,
                "maxItems": n,
                "items": {"type": "string"},
            }
        },
        "required": ["prompts"],
    }


class GeminiStoryAI:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.gemini_api_key
        self._chat_model = settings.gemini_chat_model
        self._image_model = settings.gemini_image_model

    # -- transport -------------------------------------------------------

    def _post(self, model: str, method: str, payload: dict, *, timeout: float = 60.0) -> dict:
        try:
            r = httpx.post(
                f"{_GENAI_BASE}/models/{model}:{method}",
                headers={"x-goog-api-key": self._key},
                json=payload,
                timeout=timeout,
            )
        except httpx.HTTPError as e:
            raise AIError(f"gemini request failed: {e}") from e
        if r.status_code >= 400:
            raise AIError(f"gemini {r.status_code}: {r.text[:300]}")
        return r.json()

    @staticmethod
    def _to_contents(messages: list[Message]) -> list[dict]:
        out = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            out.append({"role": role, "parts": [{"text": m["content"]}]})
        return out

    def _structured(
        self,
        system: str,
        messages: list[Message],
        schema: dict,
        *,
        temperature: float | None = None,
    ) -> dict:
        gen: dict = {"responseMimeType": "application/json", "responseSchema": schema}
        if temperature is not None:
            gen["temperature"] = temperature
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._to_contents(messages),
            "generationConfig": gen,
        }
        data = self._post(self._chat_model, "generateContent", body)

        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise AIError(f"gemini blocked: {block}")
        candidates = data.get("candidates") or []
        if not candidates:
            raise AIError("gemini: no candidates in response")
        cand = candidates[0]
        if cand.get("finishReason") in _BLOCKED_FINISH:
            raise AIError(f"gemini blocked: {cand['finishReason']}")

        text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [])
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError) as e:
            raise AIError(f"gemini: non-JSON response: {text[:200]}") from e
        tokens = int((data.get("usageMetadata") or {}).get("totalTokenCount", 0))
        return {"parsed": parsed, "tokens": tokens}

    # -- role 1: interview --------------------------------------------

    def interview(self, messages: list[Message]) -> ChatTurn:
        out = self._structured(_INTERVIEW_SYSTEM, messages, _INTERVIEW_SCHEMA, temperature=0.5)
        p = out["parsed"]
        slots = StorySlots.from_dict(p.get("slots"))
        ready = bool(p.get("ready")) and not slots.missing()
        return ChatTurn(
            reply=str(p.get("reply", "")).strip(),
            ready=ready,
            slots=slots,
            llm_tokens=out["tokens"],
        )

    # -- roles 2-4: compose ------------------------------------------

    def compose(self, messages: list[Message]) -> ComposedStory:
        draft = self._structured(_WRITER_SYSTEM, messages, _STORY_BODY_SCHEMA)
        body = draft["parsed"]
        tokens = draft["tokens"]

        review = self._structured(
            _REVIEWER_SYSTEM,
            [*messages, {"role": "assistant", "content": json.dumps(body, ensure_ascii=False)}],
            _REVIEW_SCHEMA,
        )
        rp = review["parsed"]
        tokens += review["tokens"]
        approved = bool(rp.get("approved"))
        notes = tuple(str(n) for n in rp.get("notes") or ())
        revised = rp.get("revised")
        if not approved and isinstance(revised, dict) and revised.get("pages"):
            body["title"] = revised.get("title", body["title"])
            body["pages"] = revised["pages"]
            was_revised = True
        else:
            was_revised = False

        pages_in = body["pages"]
        art_input = {
            "pages": [pg["text"] for pg in pages_in],
            "protagonist": body["protagonist"],
        }
        art = self._structured(
            _ILLUSTRATOR_SYSTEM,
            [{"role": "user", "content": json.dumps(art_input, ensure_ascii=False)}],
            _illustrator_schema(len(pages_in)),
        )
        prompts = art["parsed"].get("prompts") or []
        tokens += art["tokens"]

        pages = [
            StoryPage(
                text=pg["text"],
                image_prompt=prompts[i] if i < len(prompts) else pg["text"],
                sentence_type=pg.get("sentence_type", "descriptive"),
            )
            for i, pg in enumerate(pages_in)
        ]
        return ComposedStory(
            title=body["title"],
            protagonist=body["protagonist"],
            situation=body["situation"],
            goal=body["goal"],
            pages=pages,
            review_notes=notes,
            revised=was_revised,
            llm_tokens=tokens,
        )

    # -- illustration -----------------------------------------------

    def illustrate(self, prompt: str, protagonist: str) -> tuple[bytes, str]:
        full = (
            f"{prompt}. The same character in every image: a child named {protagonist}. "
            "Gentle flat illustration for a children's social story, soft colours, "
            "simple plain background, no text, calm and friendly."
        )
        data = self._post(
            self._image_model,
            "generateContent",
            {
                "contents": [{"parts": [{"text": full}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            },
            timeout=120.0,
        )
        candidates = data.get("candidates") or []
        if not candidates:
            raise AIError("gemini image: no candidates in response")
        cand = candidates[0]
        if cand.get("finishReason") in _BLOCKED_FINISH:
            raise AIError(f"gemini image blocked: {cand['finishReason']}")
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return base64.b64decode(inline["data"]), mime
        raise AIError("gemini image: no inline image in response")
