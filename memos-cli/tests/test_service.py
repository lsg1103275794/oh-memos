"""Tests for service management."""

import pytest

from memosctl.service import ServiceStatus, check_port_in_use, get_service_status


def test_service_status_enum():
    """Test ServiceStatus enum values."""
    assert ServiceStatus.RUNNING.value == "running"
    assert ServiceStatus.STOPPED.value == "stopped"
    assert ServiceStatus.ERROR.value == "error"


def test_check_port_in_use():
    """Test port checking (assumes 65535 is not in use)."""
    result = check_port_in_use(65535)
    assert isinstance(result, bool)


def test_get_service_status_returns_dict():
    """Test service status returns expected structure."""
    status = get_service_status()
    assert "api" in status
    assert "neo4j" in status
    assert "qdrant" in status
    assert all(isinstance(s, ServiceStatus) for s in status.values())
