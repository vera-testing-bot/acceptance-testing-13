"""Unified data access layer.

A single object owns all application state. Every component reads and writes
through typed accessors on :class:`Store` instead of stashing state in
module-level globals, component-local state, or hand-rolled ``localStorage``
blobs. Persistence is schema-versioned JSON with a migration path for the
schema-less blobs already sitting in real users' browsers, and the history
panel is a *view* over this store rather than its own drifting copy.

A transition log gives observability into the store: current state, recent
transitions, and which component wrote each value.
"""

from __future__ import annotations

import copy
import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from .display import Display

SCHEMA_VERSION = 2

Deserializer = Callable[[dict[str, Any]], dict[str, Any]]


def _now() -> float:
    return time.time()


@dataclass
class Transition:
    """A single recorded state change, for the debug/observability view."""

    key: str
    old: Any
    new: Any
    writer: str
    at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "old": self.old,
            "new": self.new,
            "writer": self.writer,
            "at": self.at,
        }


@dataclass
class State:
    """The single source of truth for application state.

    Fields are typed accessors — components go through :meth:`Store.get` /
    :meth:`Store.set` rather than reaching into private state, so the store
    owns the shape and can migrate it.
    """

    display: str = "0"
    operand: float | None = None
    operator: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, Any] = field(
        default_factory=lambda: {"theme": "light", "precision": 2}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "display": self.display,
            "operand": self.operand,
            "operator": self.operator,
            "history": copy.deepcopy(self.history),
            "settings": copy.deepcopy(self.settings),
        }


# A registry of legacy-shape -> deserializer. Each entry knows how to lift one
# prior schema-less blob shape onto the current :class:`State` shape.
_MIGRATIONS: dict[int, Deserializer] = {}


def register_legacy(version: int) -> Callable[[Deserializer], Deserializer]:
    """Register a deserializer that lifts a legacy blob of ``version``."""

    def deco(fn: Deserializer) -> Deserializer:
        _MIGRATIONS[version] = fn
        return fn

    return deco


@register_legacy(0)
def _from_v0(raw: dict[str, Any]) -> dict[str, Any]:
    """v0: schema-less browser blob with ad-hoc key names.

    The calculator grew organically, so v0 blobs use whatever key each
    component happened to pick. Map each known key onto the canonical shape;
    unknown keys are preserved under ``settings`` so nothing is silently lost.
    """
    out: dict[str, Any] = {}
    out["display"] = str(raw.get("display", raw.get("screen", "0")))
    out["operand"] = raw.get("operand", raw.get("stored", None))
    out["operator"] = raw.get("operator", raw.get("op", None))

    legacy_history = raw.get("history", raw.get("tape", []))
    out["history"] = [
        {"expr": h.get("expr", h.get("formula", "")), "result": h.get("result")}
        for h in legacy_history
    ]

    known = {
        "display",
        "screen",
        "operand",
        "stored",
        "operator",
        "op",
        "history",
        "tape",
    }
    extras = {k: v for k, v in raw.items() if k not in known}
    settings = dict(raw.get("settings", {}))
    settings.update(extras)
    out["settings"] = settings
    return out


@register_legacy(SCHEMA_VERSION)
def _from_current(raw: dict[str, Any]) -> dict[str, Any]:
    """Current schema: already canonical, pass through (minus the stamp)."""
    out = {k: v for k, v in raw.items() if k != "schema_version"}
    return out


@register_legacy(1)
def _from_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """v1: typed but pre-unified; history was a separate list that drifted."""
    out = {
        "display": raw.get("display", "0"),
        "operand": raw.get("operand"),
        "operator": raw.get("operator"),
        "history": list(raw.get("history", [])),
        "settings": dict(raw.get("settings", {})),
    }
    # The drifting history copy: v1 kept a second ``history_panel`` list that
    # could disagree with ``history``. Reconcile by preferring ``history`` and
    # appending panel-only entries so nothing is lost.
    panel = raw.get("history_panel") or raw.get("tape") or []
    seen = {json.dumps(h, sort_keys=True) for h in out["history"]}
    for entry in panel:
        marker = json.dumps(entry, sort_keys=True)
        if marker not in seen:
            out["history"].append(entry)
            seen.add(marker)
    return out


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Lift a persisted blob of any schema version onto the current shape.

    Blobs without a ``schema_version`` field are v0 (schema-less). Each step
    runs the registered deserializer for its version, then re-stamps the
    result so callers always see the canonical shape.
    """
    if not isinstance(raw, dict):
        raise TypeError(f"persisted state must be a dict, got {type(raw)!r}")
    version = raw.get("schema_version", 0)
    deserializer = _MIGRATIONS.get(version)
    if deserializer is None:
        raise ValueError(f"no migration registered for schema version {version}")
    lifted = deserializer(raw)
    lifted["schema_version"] = SCHEMA_VERSION
    return lifted


class Store:
    """Owns all application state.

    Components never hold their own copy — they call :meth:`get` / :meth:`set`
    with a ``writer`` tag identifying themselves, so the observability log
    records who changed what. History is not stored separately; it is a view
    (:meth:`history_view`) over ``state.history``.
    """

    def __init__(self, state: State | None = None) -> None:
        self._state: State = state if state is not None else State()
        self._transitions: list[Transition] = []

    @classmethod
    def load(cls, blob: dict[str, Any]) -> Store:
        """Rehydrate a store from a persisted blob, migrating as needed."""
        migrated = migrate(blob)
        state = State(
            display=migrated.get("display", "0"),
            operand=migrated.get("operand"),
            operator=migrated.get("operator"),
            history=list(migrated.get("history", [])),
            settings=dict(migrated.get("settings", {})),
        )
        return cls(state)

    def dump(self) -> dict[str, Any]:
        """Serialize the store to a schema-versioned blob for persistence."""
        out = self._state.to_dict()
        out["schema_version"] = SCHEMA_VERSION
        return out

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._state, key, default)

    def set(self, key: str, value: Any, *, writer: str) -> None:
        if not hasattr(self._state, key):
            raise KeyError(f"unknown state key: {key!r}")
        old = getattr(self._state, key)
        setattr(self._state, key, copy.deepcopy(value))
        self._transitions.append(
            Transition(
                key=key,
                old=copy.deepcopy(old),
                new=copy.deepcopy(value),
                writer=writer,
                at=_now(),
            )
        )

    def history_view(self) -> list[dict[str, Any]]:
        """History is a view over the store, not a separate copy."""
        return copy.deepcopy(self._state.history)

    def display_component(self) -> Display:
        """Build the calculator's :class:`Display` from current state.

        The calculator renders its display through this component so the
        display layer has a single owner. The store's own ``display`` value is
        untouched; rendering is a view over it, which keeps behavior unchanged
        for callers reading the raw value.
        """
        return Display(value=self._state.display)

    def debug_view(self, limit: int = 20) -> dict[str, Any]:
        """Observability: current state, recent transitions, who wrote what."""
        return {
            "state": self._state.to_dict(),
            "recent_transitions": [t.as_dict() for t in self._transitions[-limit:]],
            "writers": sorted({t.writer for t in self._transitions}),
        }

    def transitions(self) -> Iterator[Transition]:
        return iter(self._transitions)
