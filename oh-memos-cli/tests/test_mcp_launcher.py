"""Tests for MCP launcher."""

import tempfile
from pathlib import Path

import pytest

from oh_memosctl.mcp_launcher import (
    get_pid_file,
    read_pid,
    write_pid,
    remove_pid,
    is_process_running,
    get_mcp_status,
)


def test_pid_file_path():
    """Test PID file path generation."""
    path = get_pid_file("coding")
    assert "mcp_coding.pid" in str(path)


def test_write_and_read_pid():
    """Test writing and reading PID."""
    write_pid("test_mode", 12345)
    pid = read_pid("test_mode")
    assert pid == 12345
    remove_pid("test_mode")


def test_read_nonexistent_pid():
    """Test reading nonexistent PID returns None."""
    remove_pid("nonexistent_mode")
    pid = read_pid("nonexistent_mode")
    assert pid is None


def test_is_process_running_current():
    """Test is_process_running with current process."""
    import os
    assert is_process_running(os.getpid()) == True


def test_is_process_running_invalid():
    """Test is_process_running with invalid PID."""
    # PID 99999999 should not exist
    assert is_process_running(99999999) == False


def test_get_mcp_status_not_running():
    """Test get_mcp_status for non-running mode."""
    remove_pid("test_status")
    running, pid = get_mcp_status("test_status")
    assert running == False
    assert pid is None
