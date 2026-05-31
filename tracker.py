"""X account tracker: poll accounts, translate new tweets, push to Discord.

Run: python tracker.py          # persistent loop (your own machine)
     python tracker.py --once   # single pass then exit (GitHub Actions / cron)
Config: config.json (accounts, poll interval). Secrets via .env or env vars
(TWITTERAPI_IO_KEY, DISCORD_WEBHOOK_URL). STATE_PATH env var overrides state file.
"""
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Callable

import discord
import state
import translator
import twitter_api

CONFIG_PATH = "config.json"
# Overridable so cloud runners (GitHub Actions) can point at a cached path.
STATE_PATH = os.environ.get("STATE_PATH", "state.json")


@dataclass
class Deps:
    """Injectable dependencies so run_once is testable without real I/O."""
    get_new: Callable = twitter_api.get_new_tweets
    translate: Callable = None
    send: Callable = None
    sleep: Callable = time.sleep  # injectable so tests don't actually wait


def process_account(username, last_id, get_new, translate, send, api_key, webhook):
    """Process one account; return the new last_id to persist.

    - First run (last_id is None): set baseline to newest tweet, push nothing.
    - Otherwise: push each new tweet oldest->newest, advancing last_id only
      after each successful send. A failed send stops the run for this account
      so the tweet is retried next round (state is not advanced past it).
    """
    new_tweets = get_new(username, last_id, api_key)
    if not new_tweets:
        return last_id

    if last_id is None:
        # Baseline only — newest id is the last in the oldest->newest list.
        return new_tweets[-1]["id"]

    current = last_id
    for tw in new_tweets:
        translated = translate(tw["text"])
        if not send(username, tw, translated):
            break  # leave state at `current`; retry from here next round
        current = tw["id"]
    return current


def _load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"找不到 {CONFIG_PATH}，請複製 config.example.json 後填寫。")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_env():
    """Minimal .env loader (KEY=VALUE per line)."""
    env = dict(os.environ)
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def run_once(accounts, api_key, webhook, translate_fn, deps=None, state_path=STATE_PATH,
             account_delay=3):
    """Process every account exactly once and persist state. No looping.

    Used both by the persistent loop (one iteration) and the cloud --once mode.
    A small delay between accounts avoids the free-tier rate limit (HTTP 429).
    """
    if deps is None:
        deps = Deps(
            translate=translate_fn,
            send=lambda u, tw, tr: discord.send(webhook, u, tw, tr),
        )

    st = state.load_state(state_path)
    for idx, username in enumerate(accounts):
        if idx > 0 and account_delay:
            deps.sleep(account_delay)
        new_last = process_account(
            username=username,
            last_id=st.get(username),
            get_new=deps.get_new,
            translate=translate_fn,
            send=deps.send,
            api_key=api_key,
            webhook=webhook,
        )
        if new_last != st.get(username):
            st[username] = new_last
            state.save_state(state_path, st)


def _build_runtime():
    """Load config + env, validate, return (accounts, api_key, webhook, interval, translate_fn)."""
    config = _load_config()
    env = _load_env()

    api_key = env.get("TWITTERAPI_IO_KEY")
    webhook = env.get("DISCORD_WEBHOOK_URL")
    if not api_key or "your_" in (api_key or ""):
        sys.exit("請設定 TWITTERAPI_IO_KEY（.env 或環境變數）。")
    if not webhook or "xxxxx" in (webhook or ""):
        sys.exit("請設定 DISCORD_WEBHOOK_URL（.env 或環境變數）。")

    accounts = config["accounts"]
    interval = config.get("poll_interval_seconds", 60)
    do_translate = config.get("translate", True)
    target_lang = config.get("target_lang", "zh-TW")

    def translate_fn(text):
        if not do_translate:
            return None
        return translator.translate(text, target=target_lang)

    return accounts, api_key, webhook, interval, translate_fn


def main_once():
    """Single run — for GitHub Actions / cron. Process once, then exit."""
    accounts, api_key, webhook, _interval, translate_fn = _build_runtime()
    print(f"[tracker] 單次檢查 {accounts}（state: {STATE_PATH}）")
    run_once(accounts, api_key, webhook, translate_fn, state_path=STATE_PATH)
    print("[tracker] 單次檢查完成。")


def main():
    """Persistent loop — for running on your own machine."""
    accounts, api_key, webhook, interval, translate_fn = _build_runtime()
    print(f"[tracker] 開始追蹤 {accounts}，每 {interval} 秒檢查一次。Ctrl+C 結束。")
    try:
        while True:
            run_once(accounts, api_key, webhook, translate_fn, state_path=STATE_PATH)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[tracker] 已停止。")


if __name__ == "__main__":
    if "--once" in sys.argv:
        main_once()
    else:
        main()
