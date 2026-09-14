"""Calculator display component.

Owns the rendering of the calculator's display value. Previously the display
string was rendered inline by the calculator template; that responsibility now
lives in :class:`Display` so the rest of the app talks to one component.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Display:
    """A standalone calculator display component.

    The calculator renders its display value through this component instead of
    formatting it inline, so the display layer has a single owner.
    """

    value: Any = None

    def render(self) -> str:
        """Return the display text for the current value.

        ``None`` (the idle state) renders as ``"0"``; any other value is shown
        as its string form. Behavior matches the previous inline rendering.
        """
        if self.value is None:
            return "0"
        return str(self.value)

    def set(self, value: Any) -> None:
        """Stage a new value to be rendered."""
        self.value = value
