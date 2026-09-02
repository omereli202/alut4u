from __future__ import annotations

import httpx
import pytest
import respx

from app.config import Settings
from app.services.tts import get_provider
from app.services.tts.azure_he import AzureHebrewTTS
from app.services.tts.base import TTSError, TTSRequest
from app.services.tts.silent import SilentTTS


def _azure_settings(**kw) -> Settings:
    # _env_file=None: a developer's local .env (real or placeholder Azure
    # creds) must never leak into what these tests think is configured.
    defaults = dict(
        app_env="test",
        azure_speech_key="test-key",
        azure_speech_region="westeurope",
        azure_speech_voice="he-IL-HilaNeural",
    )
    return Settings(_env_file=None, **{**defaults, **kw})


# --- TTSRequest.cache_key ----------------------------------------------------


def test_cache_key_is_stable_and_sensitive_to_inputs():
    a = TTSRequest(text="שלום", voice="he-IL-HilaNeural", provider="azure-he")
    b = TTSRequest(text="שלום", voice="he-IL-HilaNeural", provider="azure-he")
    c = TTSRequest(text="שלום", voice="he-IL-AvriNeural", provider="azure-he")
    d = TTSRequest(text="להתראות", voice="he-IL-HilaNeural", provider="azure-he")

    assert a.cache_key() == b.cache_key()
    assert a.cache_key() != c.cache_key()
    assert a.cache_key() != d.cache_key()
    assert len(a.cache_key()) == 64


def test_cache_key_is_provider_scoped():
    """A stub-rendered asset must never be reachable by the digest a real
    engine would compute for the same text — see the silent-audio poisoning
    incident this field was added to fix."""
    silent = TTSRequest(text="שלום", voice="he-IL-HilaNeural", provider="silent")
    azure = TTSRequest(text="שלום", voice="he-IL-HilaNeural", provider="azure-he")
    assert silent.cache_key() != azure.cache_key()


# --- SilentTTS ----------------------------------------------------------------


def test_silent_is_wav_and_length_scales_with_text():
    short = SilentTTS().synthesize(TTSRequest(text="הי", voice="v", provider="silent"))
    long = SilentTTS().synthesize(
        TTSRequest(text="משפט ארוך יותר בהרבה מהראשון", voice="v", provider="silent")
    )
    for result in (short, long):
        assert result.mime == "audio/wav"
        assert result.audio[:4] == b"RIFF"
        assert result.audio[8:12] == b"WAVE"
        assert set(result.audio[44:]) == {0}  # PCM payload is silence
    assert len(long.audio) > len(short.audio)


# --- get_provider selection matrix --------------------------------------------


@pytest.mark.parametrize(
    "azure_speech_key,app_env,expected",
    [
        ("", "development", "silent"),
        ("test-key", "development", "azure-he"),
        ("", "production", "azure-he"),  # deliberate: fail loud, not silent, in prod
    ],
)
def test_get_provider_selection(azure_speech_key, app_env, expected):
    s = Settings(_env_file=None, app_env=app_env, azure_speech_key=azure_speech_key)
    assert get_provider(s).name == expected


# --- AzureHebrewTTS.synthesize -------------------------------------------------


@respx.mock
def test_synthesize_returns_mp3():
    route = respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(200, content=b"\xff\xfb\x90fake-mp3")
    )
    result = AzureHebrewTTS(_azure_settings()).synthesize(
        TTSRequest(text="שלום", voice="he-IL-HilaNeural", provider="azure-he")
    )
    assert route.called
    assert result.mime == "audio/mpeg"
    assert result.audio == b"\xff\xfb\x90fake-mp3"
    assert result.char_count == len("שלום")


@respx.mock
def test_ssml_and_headers():
    route = respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(200, content=b"audio")
    )
    req = TTSRequest(text="שלום עולם", voice="he-IL-HilaNeural", provider="azure-he", rate=1.0)
    AzureHebrewTTS(_azure_settings()).synthesize(req)

    sent = route.calls.last.request
    assert sent.headers["Ocp-Apim-Subscription-Key"] == "test-key"
    assert sent.headers["Content-Type"] == "application/ssml+xml"
    assert sent.headers["X-Microsoft-OutputFormat"] == req.fmt
    assert sent.headers["User-Agent"] == "alut4u"

    body = sent.content.decode("utf-8")
    assert 'xml:lang="he-IL"' in body
    assert '<voice name="he-IL-HilaNeural">' in body
    assert 'rate="1"' in body  # {req.rate:g} renders 1.0 as "1"
    assert "שלום עולם" in body


@respx.mock
def test_ssml_escapes_xml_special_characters():
    route = respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(200, content=b"audio")
    )
    req = TTSRequest(text='ילד & "בית" <טוב>', voice="he-IL-HilaNeural", provider="azure-he")
    AzureHebrewTTS(_azure_settings()).synthesize(req)

    body = route.calls.last.request.content.decode("utf-8")
    assert "&amp;" in body
    assert "&lt;" in body and "&gt;" in body
    assert "<טוב>" not in body


@respx.mock
def test_non_200_raises_ttserror():
    respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(401, text="unauthorized")
    )
    with pytest.raises(TTSError, match="azure returned 401"):
        AzureHebrewTTS(_azure_settings()).synthesize(
            TTSRequest(text="שלום", voice="v", provider="azure-he")
        )


@respx.mock
def test_rate_limited_raises_ttserror_not_5xx_surprise():
    respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(429, text="too many requests")
    )
    with pytest.raises(TTSError, match="azure returned 429"):
        AzureHebrewTTS(_azure_settings()).synthesize(
            TTSRequest(text="שלום", voice="v", provider="azure-he")
        )


@respx.mock
def test_timeout_raises_ttserror():
    respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        side_effect=httpx.ConnectTimeout("boom")
    )
    with pytest.raises(TTSError, match="azure request failed"):
        AzureHebrewTTS(_azure_settings()).synthesize(
            TTSRequest(text="שלום", voice="v", provider="azure-he")
        )


@respx.mock
def test_missing_key_raises_before_any_http_call():
    route = respx.post("https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(200, content=b"audio")
    )
    with pytest.raises(TTSError, match="AZURE_SPEECH_KEY is not configured"):
        AzureHebrewTTS(Settings(_env_file=None, app_env="test", azure_speech_key="")).synthesize(
            TTSRequest(text="שלום", voice="v", provider="azure-he")
        )
    assert not route.called


@respx.mock
def test_region_is_interpolated_into_the_endpoint():
    route = respx.post("https://northeurope.tts.speech.microsoft.com/cognitiveservices/v1").mock(
        return_value=httpx.Response(200, content=b"audio")
    )
    AzureHebrewTTS(_azure_settings(azure_speech_region="northeurope")).synthesize(
        TTSRequest(text="שלום", voice="v", provider="azure-he")
    )
    assert route.called


def test_timeout_seconds_is_configurable(monkeypatch):
    captured: dict = {}

    def _fake_post(url, *, headers, content, timeout):
        captured["timeout"] = timeout
        return httpx.Response(200, content=b"audio")

    from app.services.tts import azure_he

    monkeypatch.setattr(azure_he.httpx, "post", _fake_post)
    AzureHebrewTTS(_azure_settings(azure_speech_timeout_seconds=3.5)).synthesize(
        TTSRequest(text="שלום", voice="v", provider="azure-he")
    )
    assert captured["timeout"] == 3.5


# --- ensure_tts_asset: the integration seam where the poisoning bug actually
# lived — unit-level cache_key equality can pass while the call site still
# forgets to pass the provider through. -----------------------------------


class _FakeResult:
    def __init__(self, mime="audio/mpeg"):
        self.audio = b"fake-audio-bytes"
        self.mime = mime
        self.char_count = 4


class _FakeProvider:
    def __init__(self, name):
        self.name = name

    def synthesize(self, req):
        return _FakeResult()


def test_ensure_tts_asset_uses_provider_scoped_digest(monkeypatch):
    from app.services.tts import cache as tts_cache

    digests_looked_up: list[str] = []
    created: list[dict] = []

    def fake_find(digest):
        digests_looked_up.append(digest)

    def fake_create(**kw):
        created.append(kw)
        return {"id": f"asset-{len(created)}"}

    monkeypatch.setattr(tts_cache.media_repo, "find_tts_by_digest", fake_find)
    monkeypatch.setattr(tts_cache.media_repo, "create", fake_create)
    monkeypatch.setattr(tts_cache.storage, "upload", lambda *a, **kw: None)
    monkeypatch.setattr(tts_cache.storage, "TTS_BUCKET", "tts")

    s = Settings(_env_file=None, app_env="test", azure_speech_voice="he-IL-HilaNeural")

    monkeypatch.setattr(tts_cache, "get_provider", lambda _s: _FakeProvider("silent"))
    tts_cache.ensure_tts_asset("שלום", s)

    monkeypatch.setattr(tts_cache, "get_provider", lambda _s: _FakeProvider("azure-he"))
    tts_cache.ensure_tts_asset("שלום", s)

    assert len(digests_looked_up) == 2
    assert digests_looked_up[0] != digests_looked_up[1]


def test_ensure_tts_asset_logs_and_returns_none_on_ttserror(monkeypatch, caplog):
    from app.services.tts import cache as tts_cache

    monkeypatch.setattr(tts_cache.media_repo, "find_tts_by_digest", lambda digest: None)

    class _FailingProvider:
        name = "azure-he"

        def synthesize(self, req):
            raise TTSError("azure returned 401: unauthorized")

    monkeypatch.setattr(tts_cache, "get_provider", lambda _s: _FailingProvider())

    s = Settings(_env_file=None, app_env="test")
    with caplog.at_level("WARNING"):
        result = tts_cache.ensure_tts_asset("שלום", s)

    assert result is None
    assert any("tts synthesis failed" in r.message for r in caplog.records)
