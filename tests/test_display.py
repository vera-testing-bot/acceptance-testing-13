"""Tests for the calculator display component and formatting helper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.display import Display
from shard_app.store import Store

# --- Phase 1: extract the display component -------------------------------


def test_display_is_a_standalone_component() -> None:
    display = Display()
    assert display.value is None
    assert display.render() == "0"


def test_store_renders_display_through_display_component() -> None:
    store = Store()
    assert store.display_component().render() == "0"

    store.set("display", "42", writer="keypad")
    assert store.display_component().render() == "42"


def test_display_extraction_leaves_store_behavior_unchanged() -> None:
    store = Store()
    assert store.get("display") == "0"
    store.set("display", "9", writer="keypad")
    assert store.get("display") == "9"
    assert store.dump()["schema_version"] is not None
