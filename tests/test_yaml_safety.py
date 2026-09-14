"""Verify unsafe YAML directives are rejected.

These tests confirm that ``yaml.safe_load`` rejects unsafe YAML tags
(e.g. ``!!python/object:os.system``) and that the repository's own
``.vera/settings.yaml`` loads safely.
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SETTINGS_PATH = Path(__file__).resolve().parents[1] / ".vera" / "settings.yaml"

UNSAFE_PAYLOADS = [
    "!!python/object:os.system ['echo pwned']",
    "!!python/object/apply:os.system ['echo pwned']",
    "foo: !!python/object:os.system ['echo pwned']",
]


@pytest.mark.parametrize("payload", UNSAFE_PAYLOADS)
def test_unsafe_yaml_directive_rejected(payload: str) -> None:
    """safe_load must raise on unsafe python tags."""
    with pytest.raises(yaml.constructor.ConstructorError):
        yaml.safe_load(payload)


def test_settings_yaml_loads_safely() -> None:
    """The repo's settings.yaml must load without unsafe-tag errors."""
    data = yaml.safe_load(SETTINGS_PATH.read_text())
    assert isinstance(data, dict)
    assert data.get("auto_manage_issues") is False
