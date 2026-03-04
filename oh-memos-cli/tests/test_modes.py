"""Tests for mode definitions."""

import pytest

from oh_memosctl.modes import get_mode, list_modes, ModeNotFoundError
from oh_memosctl.modes.coding import CodingMode
from oh_memosctl.modes.student import StudentMode


def test_list_modes_returns_all():
    """Test that list_modes returns all available modes."""
    modes = list_modes()
    assert "coding" in modes
    assert "student" in modes
    assert len(modes) >= 2


def test_get_mode_coding():
    """Test getting coding mode."""
    mode = get_mode("coding")
    assert isinstance(mode, CodingMode)
    assert mode.name == "coding"
    assert mode.port == 18001


def test_get_mode_student():
    """Test getting student mode."""
    mode = get_mode("student")
    assert isinstance(mode, StudentMode)
    assert mode.name == "student"
    assert mode.port == 18002


def test_get_mode_invalid_raises():
    """Test that invalid mode raises ModeNotFoundError."""
    with pytest.raises(ModeNotFoundError):
        get_mode("nonexistent")


def test_coding_mode_memory_types():
    """Test coding mode has expected memory types."""
    mode = get_mode("coding")
    assert "BUGFIX" in mode.memory_types
    assert "ERROR_PATTERN" in mode.memory_types
    assert "DECISION" in mode.memory_types


def test_student_mode_memory_types():
    """Test student mode has expected memory types."""
    mode = get_mode("student")
    assert "LECTURE" in mode.memory_types
    assert "CONCEPT" in mode.memory_types
    assert "CITATION" in mode.memory_types
