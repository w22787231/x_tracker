"""Tests for state.py — dedup state load/save."""
import json

import state


def test_load_state_missing_file_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    assert state.load_state(str(path)) == {}


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    data = {"elonmusk": "1234", "nasa": "5678"}
    state.save_state(str(path), data)
    assert state.load_state(str(path)) == data


def test_save_overwrites_existing(tmp_path):
    path = tmp_path / "state.json"
    state.save_state(str(path), {"a": "1"})
    state.save_state(str(path), {"a": "2", "b": "9"})
    assert state.load_state(str(path)) == {"a": "2", "b": "9"}


def test_load_state_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{ not valid json", encoding="utf-8")
    assert state.load_state(str(path)) == {}
