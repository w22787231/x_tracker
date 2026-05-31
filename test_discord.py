"""Tests for discord.py — embed assembly and webhook post."""
import discord


def _tweet(translated="你好", original="hello"):
    return {
        "id": "10",
        "text": original,
        "url": "https://x.com/elonmusk/status/10",
        "createdAt": "Tue Dec 10 07:00:30 +0000 2024",
    }


def test_embed_includes_translation_and_original():
    embed = discord.build_embed("elonmusk", _tweet(), translated="你好")
    desc = embed["description"]
    assert "你好" in desc
    assert "hello" in desc
    assert embed["url"] == "https://x.com/elonmusk/status/10"
    assert "elonmusk" in embed["author"]["name"]


def test_embed_without_translation_shows_only_original():
    embed = discord.build_embed("elonmusk", _tweet(), translated=None)
    assert "hello" in embed["description"]
    # No translated line duplicated; original present once.
    assert embed["description"].count("hello") == 1


def test_chinese_original_not_duplicated():
    # When the original is already Chinese, show only the (繁中) translation,
    # not the original too — avoid the duplicated-text noise.
    tw = {
        "id": "10",
        "text": "簡體原文內容",
        "url": "https://x.com/u/status/10",
        "createdAt": "now",
    }
    embed = discord.build_embed("u", tw, translated="繁體譯文內容")
    assert "繁體譯文內容" in embed["description"]
    assert "簡體原文內容" not in embed["description"]


def test_non_chinese_original_keeps_bilingual():
    # English original -> keep original for reference alongside the translation.
    tw = {"id": "10", "text": "hello world", "url": "u", "createdAt": "now"}
    embed = discord.build_embed("u", tw, translated="你好世界")
    assert "你好世界" in embed["description"]
    assert "hello world" in embed["description"]


def test_send_posts_payload_and_returns_true_on_2xx():
    captured = {}

    def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return 204  # Discord success

    ok = discord.send(
        "https://discord.com/api/webhooks/x/y",
        "elonmusk", _tweet(), translated="你好",
        _post=fake_post,
    )
    assert ok is True
    assert captured["url"] == "https://discord.com/api/webhooks/x/y"
    assert "embeds" in captured["payload"]


def test_send_returns_false_on_error_status():
    fake_post = lambda url, payload: 400
    ok = discord.send("u", "e", _tweet(), translated="你好", _post=fake_post)
    assert ok is False


def test_send_returns_false_on_exception():
    def fake_post(url, payload):
        raise RuntimeError("network down")
    ok = discord.send("u", "e", _tweet(), translated="你好", _post=fake_post)
    assert ok is False


def test_long_message_split_into_multiple_posts():
    # A description longer than the embed limit is sent as multiple posts.
    posts = []
    fake_post = lambda url, payload: posts.append(payload) or 204
    long_tweet = {
        "id": "10", "text": "x" * 5000, "url": "u", "createdAt": "now",
    }
    ok = discord.send("w", "u", long_tweet, translated=None,
                      _post=fake_post, limit=4000)
    assert ok is True
    assert len(posts) == 2  # 5000 chars -> 2 posts at 4000-char limit
    # Each post's embed description is within the limit.
    for p in posts:
        assert len(p["embeds"][0]["description"]) <= 4000


def test_send_stops_and_returns_false_if_a_chunk_fails():
    # If a later chunk fails to post, send reports failure.
    calls = {"n": 0}

    def fake_post(url, payload):
        calls["n"] += 1
        return 204 if calls["n"] == 1 else 500

    long_tweet = {"id": "10", "text": "x" * 5000, "url": "u", "createdAt": "now"}
    ok = discord.send("w", "u", long_tweet, translated=None,
                      _post=fake_post, limit=4000)
    assert ok is False
