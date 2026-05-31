"""Translate text via Google's free translate endpoint (no key).

Mirrors the approach used in news.html. On any failure returns None so the
caller can fall back to the original text.
"""
import requests

URL = "https://translate.googleapis.com/translate_a/single"


def _http_fetch(text, target):
    """Real HTTP call. Returns parsed JSON (a nested list)."""
    resp = requests.get(
        URL,
        params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _translate_one(text, target, _fetch):
    """Translate a single chunk. Returns text or None on failure/bad shape."""
    data = _fetch(text, target)
    # Shape: [[["譯文","orig",...], ...], ...]
    if isinstance(data, list) and isinstance(data[0], list):
        return "".join(seg[0] for seg in data[0] if seg and seg[0])
    return None


def translate(text, target="zh-TW", _fetch=_http_fetch, chunk_size=1000):
    """Return translated text, or None on failure. Empty input -> ''.

    Long text is split into <=chunk_size pieces, translated separately, and
    rejoined — the free endpoint can fail or truncate on very long input.
    If any chunk fails, the whole result is None so the caller falls back to
    the original text rather than posting a partial translation.
    """
    if not text:
        return ""
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    try:
        parts = [_translate_one(c, target, _fetch) for c in chunks]
        if any(p is None for p in parts):
            return None
        return "".join(parts)
    except Exception as exc:
        print(f"[translator] failed: {exc}")
        return None
