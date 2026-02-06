#!/usr/bin/env python3
"""Tests for calendar command."""

from datetime import datetime

import pytest

from memosctl.calendar_cmd import (
    get_semester_dates,
    get_current_semester,
)


class TestGetSemesterDates:
    """Test semester date calculation."""

    def test_spring_semester(self):
        """Test spring semester dates."""
        start, end = get_semester_dates("2026-Spring")
        assert start == datetime(2026, 2, 1)
        assert end == datetime(2026, 6, 30)

    def test_fall_semester(self):
        """Test fall semester dates."""
        start, end = get_semester_dates("2025-Fall")
        assert start == datetime(2025, 9, 1)
        assert end == datetime(2025, 12, 31)

    def test_summer_semester(self):
        """Test summer semester dates."""
        start, end = get_semester_dates("2026-Summer")
        assert start == datetime(2026, 7, 1)
        assert end == datetime(2026, 8, 31)

    def test_current_semester(self):
        """Test current semester detection."""
        start, end = get_semester_dates("current")
        now = datetime.now()

        # Should return valid dates
        assert start <= end
        assert start.year >= now.year - 1
        assert end.year <= now.year + 1

    def test_invalid_semester(self):
        """Test invalid semester format falls back to current month."""
        start, end = get_semester_dates("invalid")
        now = datetime.now()

        # Should default to current month
        assert start.year == now.year
        assert start.month == now.month


class TestGetCurrentSemester:
    """Test current semester string generation."""

    def test_returns_valid_format(self):
        """Test that format is YYYY-Season."""
        result = get_current_semester()
        parts = result.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["Spring", "Summer", "Fall"]

    def test_year_is_recent(self):
        """Test that year is reasonable."""
        result = get_current_semester()
        year = int(result.split("-")[0])
        now = datetime.now()
        assert now.year - 1 <= year <= now.year


class TestCalendarCommand:
    """Test calendar CLI integration."""

    def test_run_calendar_import(self):
        """Test that run_calendar can be imported."""
        from memosctl.calendar_cmd import run_calendar
        assert callable(run_calendar)

    def test_display_functions_import(self):
        """Test that display functions can be imported."""
        from memosctl.calendar_cmd import (
            display_calendar_list,
            display_calendar_week,
            display_calendar_month,
        )
        assert callable(display_calendar_list)
        assert callable(display_calendar_week)
        assert callable(display_calendar_month)
