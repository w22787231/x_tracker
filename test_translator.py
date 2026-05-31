"""Tests for translator.py — translate with fallback to None on failure."""
import translator


def test_parses_google_response():
    # Google translate_a/single shape: [[[ "譯文", "orig", ... ]], ...]
    fake = lambda text, target: [[["你好世界", "hello world", None, None]], None, "en"]
    out = translator.translate("hello world", target="zh-TW", _fetch=fake)
    assert out == "你好世界"


def test_joins_multiple_segments():
    fake = lambda text, target: [[["第一段", "a", None], ["第二段", "b", None]], None, "en"]
    out = translator.translate("a b", target="zh-TW", _fetch=fake)
    assert out == "第一段第二段"


def test_network_error_returns_none():
    def fake(text, target):
        raise RuntimeError("down")
    assert translator.translate("hi", target="zh-TW", _fetch=fake) is None


def test_unexpected_shape_returns_none():
    fake = lambda text, target: {"unexpected": "shape"}
    assert translator.translate("hi", target="zh-TW", _fetch=fake) is None


def test_empty_text_returns_empty():
    # Don't call the endpoint for empty input.
    called = []
    fake = lambda text, target: called.append(1) or [[["x", "", None]]]
    assert translator.translate("", target="zh-TW", _fetch=fake) == ""
    assert called == []


def test_long_text_split_into_chunks_and_rejoined():
    # Text longer than the chunk size is translated in pieces and concatenated.
    # Fake echoes a marker per call so we can count calls and verify rejoin.
    calls = []

    def fake(text, target):
        calls.append(text)
        return [[[f"<{text}>", text, None]]]

    long_text = "a" * 1200  # > default 1000-char chunk -> 2 chunks
    out = translator.translate(long_text, target="zh-TW", _fetch=fake, chunk_size=1000)
    assert len(calls) == 2
    assert out == f"<{'a' * 1000}><{'a' * 200}>"


def test_chunk_failure_falls_back_to_whole_none():
    # If any chunk fails, the whole translation falls back to None
    # so the caller posts the original text instead of a half-translation.
    def fake(text, target):
        raise RuntimeError("down")

    assert translator.translate("x" * 1200, target="zh-TW", _fetch=fake, chunk_size=1000) is None
