from __future__ import annotations

from app.services.tts.base import TTSRequest


def test_cache_key_is_stable_and_sensitive_to_inputs():
    a = TTSRequest(text="שלום", voice="he-IL-HilaNeural")
    b = TTSRequest(text="שלום", voice="he-IL-HilaNeural")
    c = TTSRequest(text="שלום", voice="he-IL-AvriNeural")
    d = TTSRequest(text="להתראות", voice="he-IL-HilaNeural")

    assert a.cache_key() == b.cache_key()
    assert a.cache_key() != c.cache_key()
    assert a.cache_key() != d.cache_key()
    assert len(a.cache_key()) == 64
