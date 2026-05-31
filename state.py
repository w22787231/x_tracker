"""Dedup state: maps each tracked username to its last-pushed tweet ID."""
import json
import os


def load_state(path):
    """Return {username: last_tweet_id}. Missing or corrupt file -> {}."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path, state):
    """Write state dict to path as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
