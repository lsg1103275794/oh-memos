#!/usr/bin/env python3
"""MemOS CLI Modes - coding, student, daily, writing."""

from .base import BaseMode, ModeNotFoundError
from .coding import CodingMode
from .student import StudentMode

_MODES: dict[str, type[BaseMode]] = {
    "coding": CodingMode,
    "student": StudentMode,
}


def list_modes() -> list[str]:
    """Return list of available mode names."""
    return list(_MODES.keys())


def get_mode(name: str) -> BaseMode:
    """Get a mode instance by name."""
    if name not in _MODES:
        raise ModeNotFoundError(f"Mode '{name}' not found. Available: {list_modes()}")
    return _MODES[name]()


def get_all_modes() -> list[BaseMode]:
    """Return instances of all available modes."""
    return [mode_cls() for mode_cls in _MODES.values()]


__all__ = ["BaseMode", "ModeNotFoundError", "CodingMode", "StudentMode", 
           "list_modes", "get_mode", "get_all_modes"]
