#!/usr/bin/env python3
"""
MemOS MCP Server Calendar Handler

Handles memos_calendar tool for student mode.
Provides semester/week/day views of learning notes.
"""

from datetime import datetime, timedelta
from typing import Any

import httpx

from api_client import api_call_with_retry
from config import MEMOS_URL, MEMOS_USER, logger
from cube_manager import ensure_cube_registered
from mcp.types import TextContent

from handlers.utils import (
    api_error_response,
    cube_registration_error,
    get_cube_id_from_args,
)


def get_semester_dates(semester: str) -> tuple[datetime, datetime]:
    """Get start and end dates for a semester."""
    now = datetime.now()

    if semester == "current":
        year = now.year
        if now.month >= 9:  # Fall: Sep-Dec
            return datetime(year, 9, 1), datetime(year, 12, 31)
        elif now.month >= 2:  # Spring: Feb-Jun
            return datetime(year, 2, 1), datetime(year, 6, 30)
        else:  # Winter break
            return datetime(year - 1, 9, 1), datetime(year - 1, 12, 31)

    try:
        year_str, season = semester.split("-")
        year = int(year_str)
        if season.lower() == "spring":
            return datetime(year, 2, 1), datetime(year, 6, 30)
        elif season.lower() == "fall":
            return datetime(year, 9, 1), datetime(year, 12, 31)
        elif season.lower() == "summer":
            return datetime(year, 7, 1), datetime(year, 8, 31)
    except (ValueError, AttributeError):
        pass

    return datetime(now.year, now.month, 1), now


def get_week_dates(semester_start: datetime, week: int) -> tuple[datetime, datetime]:
    """Get start and end dates for a specific week."""
    week_start = semester_start + timedelta(weeks=week - 1)
    week_start = week_start - timedelta(days=week_start.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def format_calendar_output(
    memories: list[dict],
    semester: str,
    course: str | None,
    week: int | None,
    view: str,
) -> str:
    """Format memories as calendar view."""
    lines = []

    # Header
    if course:
        lines.append(f"## 📅 {semester} - {course}")
    else:
        lines.append(f"## 📅 {semester} 学期笔记")
    lines.append("")

    if not memories:
        lines.append("_暂无笔记_")
        return "\n".join(lines)

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for mem in memories:
        created = mem.get("created_at", mem.get("timestamp", ""))
        if isinstance(created, str) and created:
            date_str = created[:10]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(mem)

    sorted_dates = sorted(by_date.keys(), reverse=True)

    if view == "list":
        lines.append("| 日期 | 类型 | 内容摘要 |")
        lines.append("|------|------|---------|")

        for date_str in sorted_dates[:20]:
            for mem in by_date[date_str]:
                mem_type = mem.get("memory_type", mem.get("type", "NOTE"))
                content = mem.get("content", mem.get("key", ""))[:50]
                if len(content) == 50:
                    content += "..."
                content = content.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {date_str} | {mem_type} | {content} |")

    elif view == "week":
        if week:
            lines.append(f"### 第 {week} 周")
        lines.append("")

        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for date_str in sorted_dates[:7]:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                weekday = weekdays[dt.weekday()]
                lines.append(f"**{date_str} {weekday}**")
            except ValueError:
                lines.append(f"**{date_str}**")

            for mem in by_date[date_str]:
                mem_type = mem.get("memory_type", mem.get("type", "NOTE"))
                content = mem.get("content", mem.get("key", ""))[:60]
                content = content.replace("\n", " ")
                lines.append(f"- [{mem_type}] {content}")
            lines.append("")

    else:  # month view
        lines.append("| 日期 | 笔记数 | 类型分布 |")
        lines.append("|------|--------|---------|")

        for date_str in sorted_dates[:30]:
            mems = by_date[date_str]
            types = {}
            for m in mems:
                t = m.get("memory_type", "OTHER")
                types[t] = types.get(t, 0) + 1
            type_str = ", ".join(f"{k}:{v}" for k, v in types.items())
            lines.append(f"| {date_str} | {len(mems)} | {type_str} |")

    # Stats
    total = len(memories)
    type_counts = {}
    for mem in memories:
        t = mem.get("memory_type", "OTHER")
        type_counts[t] = type_counts.get(t, 0) + 1

    lines.append("")
    lines.append(f"📊 总计: {total} 条笔记")
    if type_counts:
        lines.append(f"   类型: {', '.join(f'{k}:{v}' for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))}")

    return "\n".join(lines)


async def handle_memos_calendar(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_calendar tool call."""
    cube_id = get_cube_id_from_args(arguments)
    semester = arguments.get("semester", "current")
    course = arguments.get("course")
    week = arguments.get("week")
    view = arguments.get("view", "list")

    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    start_date, end_date = get_semester_dates(semester)
    if week:
        start_date, end_date = get_week_dates(start_date, int(week))

    params = {
        "user_id": MEMOS_USER,
        "mem_cube_id": cube_id,
        "limit": 100,
    }

    success, data, status = await api_call_with_retry(
        client, "GET", f"{MEMOS_URL}/memories", cube_id,
        params=params
    )

    if success and data:
        result_data = data.get("data", {})

        memories = []
        text_mems = result_data.get("text_mem", [])
        for cube_data in text_mems:
            memories_data = cube_data.get("memories", [])
            if isinstance(memories_data, dict) and "nodes" in memories_data:
                memories.extend(memories_data["nodes"])
            elif isinstance(memories_data, list):
                memories.extend(memories_data)

        # Filter by course
        if course:
            memories = [m for m in memories
                       if course.lower() in m.get("content", "").lower()
                       or course.lower() in str(m.get("tags", [])).lower()]

        # Filter by date range
        filtered = []
        for mem in memories:
            created = mem.get("created_at", "")
            if isinstance(created, str) and created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if start_date <= dt.replace(tzinfo=None) <= end_date:
                        filtered.append(mem)
                except (ValueError, TypeError):
                    filtered.append(mem)
            else:
                filtered.append(mem)

        output = format_calendar_output(filtered, semester, course, week, view)
        return [TextContent(type="text", text=output)]

    elif data:
        return api_error_response("Calendar", data.get("message", "Unknown error"))
    else:
        return api_error_response("Calendar", f"HTTP {status}")
