#!/usr/bin/env python3
"""MemOS CLI Calendar Command - Student mode calendar view."""

from datetime import datetime
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import load_config

console = Console()


def get_semester_dates(semester: str) -> tuple[datetime, datetime]:
    """Get start and end dates for a semester.

    Args:
        semester: e.g., "2026-Spring", "2025-Fall", or "current"

    Returns:
        (start_date, end_date)
    """
    now = datetime.now()

    if semester == "current":
        year = now.year
        if now.month >= 9:  # Fall semester: Sep-Dec
            return datetime(year, 9, 1), datetime(year, 12, 31)
        elif now.month >= 2:  # Spring semester: Feb-Jun
            return datetime(year, 2, 1), datetime(year, 6, 30)
        else:  # Winter break, treat as previous fall
            return datetime(year - 1, 9, 1), datetime(year - 1, 12, 31)

    # Parse explicit semester
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

    # Default: current month
    return datetime(now.year, now.month, 1), now


def get_current_semester() -> str:
    """Get current semester string."""
    now = datetime.now()
    if now.month >= 9:
        return f"{now.year}-Fall"
    elif now.month >= 7:
        return f"{now.year}-Summer"
    elif now.month >= 2:
        return f"{now.year}-Spring"
    else:
        return f"{now.year - 1}-Fall"


def display_calendar_list(memories: list[dict], semester: str, course: Optional[str]):
    """Display memories as a list view."""
    title = f"📅 {semester}"
    if course:
        title += f" - {course}"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("日期", style="dim", width=12)
    table.add_column("类型", width=12)
    table.add_column("内容", overflow="ellipsis")

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for mem in memories:
        created = mem.get("created_at", mem.get("timestamp", ""))
        if isinstance(created, str) and created:
            date_str = created[:10]
        else:
            date_str = "Unknown"

        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(mem)

    # Sort by date descending
    for date_str in sorted(by_date.keys(), reverse=True)[:20]:
        for mem in by_date[date_str]:
            mem_type = mem.get("memory_type", mem.get("type", "NOTE"))
            content = mem.get("content", mem.get("key", ""))[:60]
            if len(content) == 60:
                content += "..."
            table.add_row(date_str, mem_type, content)

    console.print(table)

    # Stats
    total = len(memories)
    type_counts: dict[str, int] = {}
    for mem in memories:
        t = mem.get("memory_type", "OTHER")
        type_counts[t] = type_counts.get(t, 0) + 1

    stats = f"📊 总计: {total} 条笔�?
    if type_counts:
        type_str = ", ".join(f"{k}:{v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
        stats += f"\n   类型分布: {type_str}"
    console.print(stats)


def display_calendar_week(memories: list[dict], semester: str, week: Optional[int]):
    """Display memories as a week view."""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    title = f"📅 {semester}"
    if week:
        title += f" �?{week} �?

    console.print(Panel(title, style="bold cyan"))

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for mem in memories:
        created = mem.get("created_at", mem.get("timestamp", ""))
        if isinstance(created, str) and created:
            date_str = created[:10]
        else:
            date_str = "Unknown"

        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(mem)

    # Sort by date
    sorted_dates = sorted(by_date.keys(), reverse=True)[:7]

    for date_str in sorted_dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = weekdays[dt.weekday()]
            console.print(f"\n[bold]{date_str} {weekday}[/bold]")
        except ValueError:
            console.print(f"\n[bold]{date_str}[/bold]")

        for mem in by_date[date_str]:
            mem_type = mem.get("memory_type", mem.get("type", "NOTE"))
            content = mem.get("content", mem.get("key", ""))[:60]
            console.print(f"  [{mem_type}] {content}")


def display_calendar_month(memories: list[dict], semester: str):
    """Display memories as a month summary."""
    title = f"📅 {semester} 月度概览"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("日期", width=12)
    table.add_column("笔记�?, justify="right", width=8)
    table.add_column("类型分布")

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for mem in memories:
        created = mem.get("created_at", mem.get("timestamp", ""))
        if isinstance(created, str) and created:
            date_str = created[:10]
        else:
            date_str = "Unknown"

        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(mem)

    for date_str in sorted(by_date.keys(), reverse=True)[:30]:
        mems = by_date[date_str]
        types: dict[str, int] = {}
        for m in mems:
            t = m.get("memory_type", "OTHER")
            types[t] = types.get(t, 0) + 1
        type_str = ", ".join(f"{k}:{v}" for k, v in types.items())
        table.add_row(date_str, str(len(mems)), type_str)

    console.print(table)


def run_calendar(
    semester: str = "current",
    course: Optional[str] = None,
    week: Optional[int] = None,
    view: str = "list",
    cube_id: Optional[str] = None,
) -> bool:
    """Run calendar view command.

    Args:
        semester: Semester filter (e.g., "2026-Spring", "current")
        course: Course name filter
        week: Week number filter
        view: View type (list, week, month)
        cube_id: Memory cube ID

    Returns:
        True if successful
    """
    config = load_config()
    cube_id = cube_id or config.default_cube

    # Resolve semester
    if semester == "current":
        semester_display = get_current_semester()
    else:
        semester_display = semester

    console.print(f"[dim]Loading calendar for {semester_display}...[/dim]")

    # Query memories from API
    try:
        with httpx.Client(timeout=30.0) as client:
            params = {
                "user_id": config.user_id,
                "mem_cube_id": cube_id,
                "limit": 100,
            }

            response = client.get(f"{config.api_url}/memories", params=params)

            if response.status_code != 200:
                console.print(f"[red]Error: API returned {response.status_code}[/red]")
                return False

            data = response.json()
            result_data = data.get("data", {})

            # Extract memories
            memories = []
            text_mems = result_data.get("text_mem", [])
            for cube_data in text_mems:
                memories_data = cube_data.get("memories", [])
                if isinstance(memories_data, dict) and "nodes" in memories_data:
                    memories.extend(memories_data["nodes"])
                elif isinstance(memories_data, list):
                    memories.extend(memories_data)

            # Filter by course if specified
            if course:
                memories = [m for m in memories
                           if course.lower() in m.get("content", "").lower()
                           or course.lower() in str(m.get("tags", [])).lower()]

            # Filter by date range
            start_date, end_date = get_semester_dates(semester)
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

            memories = filtered

            if not memories:
                console.print(f"[yellow]暂无 {semester_display} 的笔记[/yellow]")
                return True

            # Display based on view type
            if view == "list":
                display_calendar_list(memories, semester_display, course)
            elif view == "week":
                display_calendar_week(memories, semester_display, week)
            elif view == "month":
                display_calendar_month(memories, semester_display)
            else:
                display_calendar_list(memories, semester_display, course)

            return True

    except httpx.RequestError as e:
        console.print(f"[red]Error connecting to API: {e}[/red]")
        console.print("[dim]Make sure MemOS API is running (memosctl status)[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
