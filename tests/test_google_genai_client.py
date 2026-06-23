import os

from ztare.common.google_genai_client import build_google_genai_client


def test_google_genai_client_masks_non_selected_key_and_restores_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    seen: dict[str, object] = {}

    def fake_client_factory(*, api_key: str | None = None):
        seen["api_key"] = api_key
        seen["gemini_visible"] = os.environ.get("GEMINI_API_KEY")
        seen["google_visible"] = os.environ.get("GOOGLE_API_KEY")
        return {"ok": True}

    client = build_google_genai_client(fake_client_factory, api_key="gemini-key")

    assert client == {"ok": True}
    assert seen == {
        "api_key": "gemini-key",
        "gemini_visible": "gemini-key",
        "google_visible": None,
    }
    assert os.environ["GEMINI_API_KEY"] == "gemini-key"
    assert os.environ["GOOGLE_API_KEY"] == "google-key"


def test_google_genai_client_preserves_google_key_selection(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    seen: dict[str, object] = {}

    def fake_client_factory(*, api_key: str | None = None):
        seen["api_key"] = api_key
        seen["gemini_visible"] = os.environ.get("GEMINI_API_KEY")
        seen["google_visible"] = os.environ.get("GOOGLE_API_KEY")
        return {"ok": True}

    build_google_genai_client(fake_client_factory, api_key="google-key")

    assert seen == {
        "api_key": "google-key",
        "gemini_visible": None,
        "google_visible": "google-key",
    }
