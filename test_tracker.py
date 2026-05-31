"""Tests for tracker.py — per-account processing and state discipline."""
import tracker


def _tweet(i):
    return {"id": str(i), "text": f"t{i}", "url": f"https://x.com/u/status/{i}", "createdAt": "now"}


def test_first_run_sets_baseline_without_pushing():
    # No prior state -> establish baseline at newest id, push nothing.
    sent = []
    new_last = tracker.process_account(
        username="u",
        last_id=None,
        get_new=lambda u, since, key: [_tweet(10), _tweet(11), _tweet(12)],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: sent.append(tw["id"]) or True,
        api_key="k",
        webhook="w",
    )
    assert sent == []          # no flood on first run
    assert new_last == "12"    # baseline = newest tweet id


def test_pushes_new_tweets_and_advances_state():
    sent = []
    new_last = tracker.process_account(
        username="u",
        last_id="10",
        get_new=lambda u, since, key: [_tweet(11), _tweet(12)],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: sent.append(tw["id"]) or True,
        api_key="k",
        webhook="w",
    )
    assert sent == ["11", "12"]
    assert new_last == "12"


def test_state_not_advanced_past_failed_send():
    # Tweet 11 sends OK, 12 fails -> state stops at 11 so 12 retries next round.
    sent = []

    def send(u, tw, tr):
        if tw["id"] == "12":
            return False
        sent.append(tw["id"])
        return True

    new_last = tracker.process_account(
        username="u",
        last_id="10",
        get_new=lambda u, since, key: [_tweet(11), _tweet(12), _tweet(13)],
        translate=lambda text: "譯",
        send=send,
        api_key="k",
        webhook="w",
    )
    assert sent == ["11"]      # 13 never attempted after 12 failed
    assert new_last == "11"    # state stops before the failed tweet


def test_translation_failure_still_sends_with_none():
    received = []
    tracker.process_account(
        username="u",
        last_id="10",
        get_new=lambda u, since, key: [_tweet(11)],
        translate=lambda text: None,  # translation down
        send=lambda u, tw, tr: received.append(tr) or True,
        api_key="k",
        webhook="w",
    )
    assert received == [None]  # send called with translated=None -> original only


def test_no_new_tweets_keeps_state():
    new_last = tracker.process_account(
        username="u",
        last_id="10",
        get_new=lambda u, since, key: [],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: True,
        api_key="k",
        webhook="w",
    )
    assert new_last == "10"


def test_run_once_processes_all_accounts_and_persists(tmp_path):
    # run_once should process every account exactly once and save state,
    # without looping.
    state_path = tmp_path / "state.json"
    sent = []

    deps = tracker.Deps(
        get_new=lambda u, since, key: [_tweet(11)] if since == "10" else [],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: sent.append((u, tw["id"])) or True,
    )
    # Pre-seed state so accounts are past first-run baseline.
    import state as state_mod
    state_mod.save_state(str(state_path), {"a": "10", "b": "10"})

    tracker.run_once(
        accounts=["a", "b"],
        api_key="k",
        webhook="w",
        translate_fn=deps.translate,
        deps=deps,
        state_path=str(state_path),
        account_delay=0,
    )

    assert ("a", "11") in sent
    assert ("b", "11") in sent
    # State advanced and persisted.
    saved = state_mod.load_state(str(state_path))
    assert saved == {"a": "11", "b": "11"}


def test_run_once_first_run_sets_baseline_no_send(tmp_path):
    state_path = tmp_path / "state.json"
    sent = []
    deps = tracker.Deps(
        get_new=lambda u, since, key: [_tweet(10), _tweet(12)],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: sent.append(tw["id"]) or True,
    )
    tracker.run_once(
        accounts=["a"],
        api_key="k",
        webhook="w",
        translate_fn=deps.translate,
        deps=deps,
        state_path=str(state_path),
        account_delay=0,
    )
    assert sent == []  # no flood on first run
    import state as state_mod
    assert state_mod.load_state(str(state_path)) == {"a": "12"}


def test_run_once_delays_between_accounts_to_avoid_rate_limit(tmp_path):
    # A delay is inserted between accounts (but not before the first) so the
    # free-tier rate limit isn't tripped.
    slept = []
    deps = tracker.Deps(
        get_new=lambda u, since, key: [],
        translate=lambda text: "譯",
        send=lambda u, tw, tr: True,
        sleep=lambda s: slept.append(s),
    )
    tracker.run_once(
        accounts=["a", "b", "c"],
        api_key="k",
        webhook="w",
        translate_fn=deps.translate,
        deps=deps,
        state_path=str(tmp_path / "s.json"),
        account_delay=3,
    )
    assert slept == [3, 3]  # 3 accounts -> 2 gaps
