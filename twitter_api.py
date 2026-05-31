"""Fetch new tweets for a username from twitterapi.io, filtered by since_id."""
import requests

BASE_URL = "https://api.twitterapi.io/twitter/user/last_tweets"


def _http_fetch(username, api_key):
    """Real HTTP call. Returns the parsed JSON response dict."""
    resp = requests.get(
        BASE_URL,
        params={"userName": username},
        headers={"X-API-Key": api_key},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def get_new_tweets(username, since_id, api_key, _fetch=_http_fetch):
    """Return tweets newer than since_id, oldest->newest.

    since_id=None -> return all available tweets (oldest->newest).
    Any error (network, API status!=success) -> return [] so the caller's
    poll loop keeps running and retries next round.
    """
    try:
        data = _fetch(username, api_key)
    except Exception as exc:  # network / parse error
        print(f"[twitter_api] fetch failed for @{username}: {exc}")
        return []

    if data.get("status") != "success":
        print(f"[twitter_api] API error for @{username}: {data.get('msg') or data.get('message')}")
        return []

    # Tweets are nested under "data"; older API docs show a top-level "tweets".
    # Support both so we are robust to either response shape.
    raw = data.get("data", {}).get("tweets") or data.get("tweets", [])

    # API returns newest-first; reverse to oldest-first for chronological push.
    tweets = list(reversed(raw))

    if since_id is not None:
        tweets = [t for t in tweets if int(t["id"]) > int(since_id)]

    return [
        {
            "id": str(t["id"]),
            "text": t.get("text", ""),
            "url": t.get("url", ""),
            "createdAt": t.get("createdAt", ""),
        }
        for t in tweets
    ]
