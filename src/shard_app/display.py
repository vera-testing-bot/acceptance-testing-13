"""Calculator display component.

Owns the rendering of the calculator's display value. Previously the display
string was rendered inline by the calculator template; that responsibility now
lives in :class:`Display`, backed by the single :func:`format_value` helper so
every rendered value flows through one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_PRECISION = 2


def format_value(value: Any, *, precision: int = DEFAULT_PRECISION) -> str:
    """Render a raw calculator value as the display string.

    Every value shown on the display flows through this single helper so the
    formatting rules live in one place:

    - ``None`` renders as the idle screen ``"0"``.
    - Booleans render as their literal text (they are not numbers).
    - Integers render without a decimal point.
    - Floats render at ``precision`` decimals, collapsing ``-0`` to ``"0"``
      and dropping trailing zeros so ``7.00`` reads as ``"7"``.
    - Anything else is passed through as its string form unchanged.
    """
    if value is None:
        return "0"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        numeric = float(value)
        text = f"{numeric:.{precision}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        # Collapse any representation that rounds to zero (e.g. "-0",
        # "-0.00" after stripping, or genuine -0.0) to the plain "0"
        # idle glyph, matching the documented -0 → "0" contract.
        if text.lstrip("-").lstrip("0") == "":
            return "0"
        return text
    return str(value)


@dataclass
class Display:
    """A standalone calculator display component.

    The calculator renders its display value through this component instead of
    formatting it inline, so the display layer has a single owner.
    """

    value: Any = None
    precision: int = DEFAULT_PRECISION
    aria_live: str = "polite"

    def render(self) -> str:
        """Return the formatted display text, routing through format_value."""
        return format_value(self.value, precision=self.precision)

    def set(self, value: Any) -> None:
        """Stage a new value; :meth:`render` formats it on demand."""
        self.value = value

    def aria_attributes(self) -> dict[str, str]:
        """Accessibility metadata for the display element.

        An ``aria-live`` region lets screen readers announce display updates;
        ``aria-atomic`` ensures the whole value is read rather than fragments.
        This metadata carries no visual styling, so rendering is unchanged.
        """
        return {"aria-live": self.aria_live, "aria-atomic": "true"}
