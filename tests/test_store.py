"""Tests for the unified data access layer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.store import (
    SCHEMA_VERSION,
    State,
    Store,
    migrate,
)


def test_store_has_typed_accessors_for_every_state_field() -> None:
    store = Store()
    assert store.get("display") == "0"
    assert store.get("operand") is None
    assert store.get("operator") is None
    assert store.get("history") == []
    assert store.get("settings") == {"theme": "light", "precision": 2}


def test_set_records_writer_in_transition_log() -> None:
    store = Store()
    store.set("display", "42", writer="keypad")
    store.set("operand", 7.0, writer="engine")

    transitions = list(store.transitions())
    assert [t.writer for t in transitions] == ["keypad", "engine"]
    assert transitions[0].key == "display"
    assert transitions[0].old == "0"
    assert transitions[0].new == "42"
    assert transitions[1].key == "operand"
    assert transitions[1].old is None
    assert transitions[1].new == 7.0


def test_set_rejects_unknown_keys() -> None:
    store = Store()
    try:
        store.set("nope", 1, writer="x")
    except KeyError:
        pass
    else:
        raise AssertionError("set on unknown key should raise KeyError")


def test_dump_round_trips_through_load() -> None:
    store = Store()
    store.set("display", "9", writer="keypad")
    store.set("settings", {"theme": "dark", "precision": 4}, writer="settings-panel")
    blob = store.dump()
    assert blob["schema_version"] == SCHEMA_VERSION

    restored = Store.load(blob)
    assert restored.get("display") == "9"
    assert restored.get("settings") == {"theme": "dark", "precision": 4}


def test_history_is_a_view_not_a_separate_copy() -> None:
    store = Store()
    store.set("history", [{"expr": "1+1", "result": 2}], writer="engine")
    view = store.history_view()
    assert view == [{"expr": "1+1", "result": 2}]
    view.append({"expr": "x", "result": 9})
    assert store.history_view() == [{"expr": "1+1", "result": 2}]


def test_debug_view_shows_state_transitions_and_writers() -> None:
    store = Store()
    store.set("display", "5", writer="keypad")
    store.set("display", "6", writer="keypad")
    store.set("operator", "+", writer="keypad")

    view = store.debug_view(limit=2)
    assert view["state"]["display"] == "6"
    assert len(view["recent_transitions"]) == 2
    assert view["writers"] == ["keypad"]
    assert view["recent_transitions"][-1]["new"] == "+"


def test_migrate_v0_schema_less_blob_uses_legacy_keys() -> None:
    raw = {
        "screen": "12",
        "stored": 3.0,
        "op": "+",
        "tape": [{"formula": "1+2", "result": 3}],
        "theme": "dark",
    }
    migrated = migrate(raw)
    assert migrated["schema_version"] == SCHEMA_VERSION
    assert migrated["display"] == "12"
    assert migrated["operand"] == 3.0
    assert migrated["operator"] == "+"
    assert migrated["history"] == [{"expr": "1+2", "result": 3}]
    assert migrated["settings"]["theme"] == "dark"


def test_migrate_v1_reconciles_drifting_history_panel() -> None:
    shared = [{"expr": "1+1", "result": 2}]
    panel_only = [{"expr": "2+2", "result": 4}]
    raw = {
        "schema_version": 1,
        "display": "4",
        "operand": 1.0,
        "operator": "+",
        "history": shared,
        "history_panel": shared + panel_only,
        "settings": {"theme": "light"},
    }
    migrated = migrate(raw)
    assert migrated["schema_version"] == SCHEMA_VERSION
    assert migrated["history"] == [
        {"expr": "1+1", "result": 2},
        {"expr": "2+2", "result": 4},
    ]


def test_migrate_unknown_version_raises() -> None:
    try:
        migrate({"schema_version": 999})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown schema version should raise ValueError")


def test_migrate_non_dict_raises() -> None:
    for bad in ("not a dict", 42, None):
        try:
            migrate(bad)  # type: ignore[arg-type]
        except TypeError:
            pass
        else:
            raise AssertionError(f"migrate should reject {bad!r}")


def test_load_runs_migration_then_exposes_typed_state() -> None:
    raw = {"screen": "8", "stored": 2.0, "op": "*"}
    store = Store.load(raw)
    assert isinstance(store.get("operand"), float | int) or store.get("operand") is None
    assert store.get("display") == "8"
    assert store.get("operator") == "*"
    assert store.dump()["schema_version"] == SCHEMA_VERSION


def test_state_default_is_isolated_per_instance() -> None:
    a = State()
    b = State()
    a.history.append({"expr": "1", "result": 1})
    a.settings["theme"] = "dark"
    assert b.history == []
    assert b.settings == {"theme": "light", "precision": 2}
