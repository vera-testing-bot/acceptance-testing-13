"""Tests for the calculator display component and formatting helper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.display import DEFAULT_PRECISION, Display, format_value
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


# --- Phase 2: single formatting helper ------------------------------------


def test_format_value_none_is_idle_screen() -> None:
    assert format_value(None) == "0"


def test_format_value_int_has_no_decimal() -> None:
    assert format_value(7) == "7"
    assert format_value(-3) == "-3"


def test_format_value_float_strips_trailing_zeros() -> None:
    assert format_value(7.0) == "7"
    assert format_value(3.5) == "3.5"
    assert format_value(3.14) == "3.14"


def test_format_value_respects_precision() -> None:
    assert format_value(3.14159, precision=3) == "3.142"
    assert format_value(2.71828, precision=1) == "2.7"


def test_format_value_collapses_negative_zero() -> None:
    assert format_value(-0.0) == "0"
    assert format_value(-0.000, precision=2) == "0"


def test_format_value_passes_non_numeric_strings_through() -> None:
    assert format_value("Error") == "Error"
    assert format_value("8") == "8"


def test_format_value_bool_is_not_a_number() -> None:
    assert format_value(True) == "True"
    assert format_value(False) == "False"


def test_format_value_default_precision_constant() -> None:
    assert DEFAULT_PRECISION == 2


def test_display_render_routes_through_format_value() -> None:
    assert Display(value=None).render() == "0"
    assert Display(value=7.0).render() == "7"
    assert Display(value=3.14159, precision=3).render() == "3.142"
    assert Display(value="Error").render() == "Error"


def test_display_set_routes_through_format_value_on_render() -> None:
    display = Display()
    display.set(3.5)
    assert display.render() == "3.5"


def test_store_display_component_uses_settings_precision() -> None:
    store = Store()
    store.set("settings", {"theme": "light", "precision": 3}, writer="settings")
    store.set("display", 3.14159, writer="engine")
    assert store.display_component().render() == "3.142"
