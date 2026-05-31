"""Tests for twitter_api.py — since_id filtering and parsing."""
import twitter_api


def _fake_tweets(*ids):
    # API returns newest-first; build that order.
    return {
        "status": "success",
        "tweets": [
            {
                "id": str(i),
                "text": f"tweet {i}",
                "url": f"https://x.com/u/status/{i}",
                "createdAt": "Tue Dec 10 07:00:30 +0000 2024",
            }
            for i in ids
        ],
    }


def test_filters_to_only_newer_than_since_id():
    # Newest-first: 30, 20, 10. since_id=10 -> keep 20, 30.
    fetch = lambda username, key: _fake_tweets(30, 20, 10)
    out = twitter_api.get_new_tweets("u", since_id="10", api_key="k", _fetch=fetch)
    assert [t["id"] for t in out] == ["20", "30"]  # returned oldest->newest


def test_no_since_id_returns_all_oldest_first():
    fetch = lambda username, key: _fake_tweets(30, 20, 10)
    out = twitter_api.get_new_tweets("u", since_id=None, api_key="k", _fetch=fetch)
    assert [t["id"] for t in out] == ["10", "20", "30"]


def test_since_id_at_newest_returns_empty():
    fetch = lambda username, key: _fake_tweets(30, 20, 10)
    out = twitter_api.get_new_tweets("u", since_id="30", api_key="k", _fetch=fetch)
    assert out == []


def test_parses_fields():
    fetch = lambda username, key: _fake_tweets(10)
    out = twitter_api.get_new_tweets("u", since_id=None, api_key="k", _fetch=fetch)
    t = out[0]
    assert t["id"] == "10"
    assert t["text"] == "tweet 10"
    assert t["url"] == "https://x.com/u/status/10"
    assert "createdAt" in t


def test_api_error_returns_empty():
    def fetch(username, key):
        raise RuntimeError("network down")
    out = twitter_api.get_new_tweets("u", since_id=None, api_key="k", _fetch=fetch)
    assert out == []


def test_status_error_returns_empty():
    fetch = lambda username, key: {"status": "error", "message": "bad", "tweets": []}
    out = twitter_api.get_new_tweets("u", since_id=None, api_key="k", _fetch=fetch)
    assert out == []


def test_parses_nested_data_tweets_shape():
    # Real twitterapi.io shape: tweets live under data.tweets, not top-level.
    nested = {
        "status": "success",
        "data": {
            "tweets": [
                {"id": "20", "text": "newer", "url": "u20", "createdAt": "now"},
                {"id": "10", "text": "older", "url": "u10", "createdAt": "now"},
            ]
        },
    }
    fetch = lambda username, key: nested
    out = twitter_api.get_new_tweets("u", since_id=None, api_key="k", _fetch=fetch)
    assert [t["id"] for t in out] == ["10", "20"]  # oldest->newest
