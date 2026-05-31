"""Build Discord embeds from tweets and post them to an Incoming Webhook."""
import requests


def _http_post(url, payload):
    """Real HTTP call. Returns the HTTP status code."""
    resp = requests.post(url, json=payload, timeout=15)
    return resp.status_code


def _is_mostly_chinese(text):
    """True if the text is predominantly CJK characters (already Chinese)."""
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    letters = sum(1 for ch in text if ch.isalpha() or "一" <= ch <= "鿿")
    return letters > 0 and cjk / letters > 0.5


def build_embed(username, tweet, translated):
    """Assemble a Discord embed. translated=None -> show only the original text.

    Description shows the translated text. The original is appended for
    reference only when it is in a different language; if the original is
    already Chinese, showing it again would just duplicate the translation,
    so it is omitted.
    """
    original = tweet.get("text", "")
    if translated:
        if _is_mostly_chinese(original):
            description = translated  # original is already Chinese; no duplicate
        else:
            description = f"{translated}\n\n> {original}"
    else:
        description = original

    return {
        "author": {"name": f"@{username}"},
        "description": description,
        "url": tweet.get("url", ""),
        "footer": {"text": tweet.get("createdAt", "")},
    }


EMBED_LIMIT = 4000  # Discord embed description max is 4096; leave headroom.


def send(webhook_url, username, tweet, translated, _post=_http_post, limit=EMBED_LIMIT):
    """Post one tweet to Discord. Returns True if all parts post successfully.

    If the assembled description exceeds `limit`, it is split into multiple
    posts sent in order. Any failed post returns False so the caller leaves
    state unchanged and retries this tweet next round.
    """
    embed = build_embed(username, tweet, translated)
    description = embed["description"]
    chunks = [description[i:i + limit] for i in range(0, len(description), limit)] or [""]

    try:
        for idx, chunk in enumerate(chunks):
            part = dict(embed)
            part["description"] = chunk
            if idx > 0:
                # Only the first part carries the author header / tweet link.
                part.pop("author", None)
                part.pop("url", None)
                part.pop("footer", None)
            status = _post(webhook_url, {"embeds": [part]})
            if not 200 <= status < 300:
                print(f"[discord] webhook returned HTTP {status}")
                return False
    except Exception as exc:
        print(f"[discord] post failed: {exc}")
        return False
    return True
