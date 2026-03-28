"""
Weekly Planner Auto-Transfer Script
------------------------------------
Automatically transfers high-priority tasks from Data.xlsx into a
'📅 Weekly Planner' sheet, assigning each task to the correct weekday
based on:
  1. Due date column (if present) — task goes to that specific day.
  2. Priority tier — tasks without a due date are distributed across
     the current week: Tier 1 → Mon/Tue, Tier 2 → Wed/Thu, Other → Fri.

Run:
    python weekly_planner.py
    python weekly_planner.py --week 2026-04-06   # specific Monday
    python weekly_planner.py --file MyData.xlsx  # custom file
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from typing import Any

import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FILE = "Data.xlsx"
TASKS_SHEET = "📧 Missing Emails (328)"
PLANNER_SHEET = "📅 Weekly Planner"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Tier → preferred weekday index (0=Mon … 4=Fri)
TIER_DAY_MAP = {
    "Tier 1": [0, 1],   # Monday, Tuesday
    "Tier 2": [2, 3],   # Wednesday, Thursday
}
DEFAULT_DAYS = [4]      # Friday for everything else

# Column indices in the tasks sheet (0-based)
COL_ABM = 0    # ABM Priority
COL_TIER = 1   # Tier
COL_PERSONA = 2
COL_COMPANY = 3
COL_FIRST = 4
COL_LAST = 5
COL_TITLE = 6
COL_LINKEDIN = 7
COL_WEBSITE = 8
COL_SIZE = 9
COL_METHOD = 10
COL_PROMPT = 11
COL_DUE = 12   # Optional "Due Date" column (added by user later)

# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------

DAY_COLOURS = {
    "Monday":    "4472C4",   # blue
    "Tuesday":   "ED7D31",   # orange
    "Wednesday": "A9D18E",   # green
    "Thursday":  "FFD966",   # yellow
    "Friday":    "9DC3E6",   # light blue
}

TIER_BADGE = {
    "Tier 1": "C00000",   # dark red
    "Tier 2": "FF6600",   # orange
}


def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _font(bold=False, color="000000", size=11) -> Font:
    return Font(bold=bold, color=color, size=size)


def _border() -> Border:
    thin = Side(style="thin", color="BFBFBF")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _center() -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=True)


def _left() -> Alignment:
    return Alignment(horizontal="left", vertical="center", wrap_text=True)


# ---------------------------------------------------------------------------
# Week helpers
# ---------------------------------------------------------------------------

def current_monday() -> date:
    """Return the Monday of the current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def week_dates(monday: date) -> list[date]:
    return [monday + timedelta(days=i) for i in range(5)]


def parse_date(value: Any) -> date | None:
    """Try to coerce a cell value to a date."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                from datetime import datetime
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_tasks(wb: openpyxl.Workbook) -> list[dict]:
    """Read all rows from the tasks sheet. Returns list of dicts."""
    if TASKS_SHEET not in wb.sheetnames:
        raise ValueError(f"Sheet '{TASKS_SHEET}' not found in workbook.")

    ws = wb[TASKS_SHEET]
    tasks = []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if row_idx == 0:
            continue  # skip header

        abm = str(row[COL_ABM] or "").strip().upper()
        if abm != "YES":
            continue   # only transfer ABM priority tasks

        tier = str(row[COL_TIER] or "").strip()
        due_raw = row[COL_DUE] if len(row) > COL_DUE else None
        due_date = parse_date(due_raw)

        tasks.append({
            "abm": abm,
            "tier": tier,
            "persona": row[COL_PERSONA],
            "company": row[COL_COMPANY],
            "first_name": row[COL_FIRST],
            "last_name": row[COL_LAST],
            "job_title": row[COL_TITLE],
            "linkedin": row[COL_LINKEDIN],
            "website": row[COL_WEBSITE],
            "company_size": row[COL_SIZE],
            "method": row[COL_METHOD],
            "due_date": due_date,
        })

    return tasks


# ---------------------------------------------------------------------------
# Task-to-day assignment
# ---------------------------------------------------------------------------

def assign_day(task: dict, week: list[date]) -> date:
    """Return the weekday date this task should appear on."""

    # 1. Explicit due date within this week
    if task["due_date"] and task["due_date"] in week:
        return task["due_date"]

    # 2. Explicit due date in the future — skip for this week
    if task["due_date"] and task["due_date"] > week[-1]:
        return None

    # 3. Tier-based auto-assignment
    tier = task["tier"]
    preferred_indices = TIER_DAY_MAP.get(tier, DEFAULT_DAYS)

    # Pick the day with the fewest tasks already assigned; break ties by index
    task["_preferred_indices"] = preferred_indices
    return None   # resolved in batch below


def assign_all(tasks: list[dict], week: list[date]) -> dict[date, list[dict]]:
    """
    Assign every task to a weekday date, balancing load.
    Returns {date: [task, ...]} for Mon–Fri.
    """
    buckets: dict[date, list[dict]] = {d: [] for d in week}
    deferred: list[dict] = []

    # First pass: tasks with an explicit due date this week
    for task in tasks:
        if task["due_date"] and task["due_date"] in week:
            buckets[task["due_date"]].append(task)
        else:
            deferred.append(task)

    # Second pass: balance remaining tasks by tier preference
    for task in deferred:
        tier = task["tier"]
        preferred_indices = TIER_DAY_MAP.get(tier, DEFAULT_DAYS)
        preferred_dates = [week[i] for i in preferred_indices if i < len(week)]

        # Pick the least-loaded preferred day
        chosen = min(preferred_dates, key=lambda d: len(buckets[d]))
        buckets[chosen].append(task)

    return buckets


# ---------------------------------------------------------------------------
# Sheet writing
# ---------------------------------------------------------------------------

PLANNER_HEADERS = [
    "Priority", "Tier", "Persona", "Company",
    "Contact Name", "Job Title", "Website",
    "Enrichment Method", "Status",
]

COL_WIDTHS = [10, 10, 18, 28, 22, 30, 32, 45, 14]


def _write_day_header(ws, row: int, day_name: str, day_date: date,
                      task_count: int, start_col: int = 1):
    colour = DAY_COLOURS[day_name]
    label = f"{day_name}  —  {day_date.strftime('%d %b %Y')}  ({task_count} tasks)"
    cell = ws.cell(row=row, column=start_col, value=label)
    cell.fill = _fill(colour)
    cell.font = _font(bold=True, color="FFFFFF", size=12)
    cell.alignment = _center()
    # Merge across all columns
    ws.merge_cells(
        start_row=row, start_column=start_col,
        end_row=row, end_column=start_col + len(PLANNER_HEADERS) - 1
    )
    ws.row_dimensions[row].height = 22


def _write_column_headers(ws, row: int, day_name: str):
    colour = DAY_COLOURS[day_name]
    for col_idx, header in enumerate(PLANNER_HEADERS, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.fill = _fill(colour)
        cell.font = _font(bold=True, color="000000", size=10)
        cell.alignment = _center()
        cell.border = _border()
    ws.row_dimensions[row].height = 18


def _write_task_row(ws, row: int, task: dict, row_num_in_day: int):
    # Alternating row shade
    bg = "F2F2F2" if row_num_in_day % 2 == 0 else "FFFFFF"

    tier = task.get("tier", "")
    tier_colour = TIER_BADGE.get(tier, "404040")
    name = f"{task.get('first_name', '')} {task.get('last_name', '')}".strip()

    values = [
        "HIGH",
        tier,
        task.get("persona", ""),
        task.get("company", ""),
        name,
        task.get("job_title", ""),
        task.get("website", ""),
        task.get("method", ""),
        "To Do",
    ]

    for col_idx, val in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col_idx, value=val)
        cell.fill = _fill(bg)
        cell.border = _border()

        if col_idx == 1:   # Priority badge
            cell.font = _font(bold=True, color="C00000", size=10)
            cell.alignment = _center()
        elif col_idx == 2:  # Tier badge
            cell.font = _font(bold=True, color=tier_colour, size=10)
            cell.alignment = _center()
        elif col_idx == 9:  # Status
            cell.font = _font(color="595959", size=10)
            cell.alignment = _center()
        else:
            cell.font = _font(size=10)
            cell.alignment = _left()

    ws.row_dimensions[row].height = 30


def _write_spacer(ws, row: int):
    ws.row_dimensions[row].height = 8


def build_planner_sheet(wb: openpyxl.Workbook, buckets: dict[date, list[dict]]):
    """Create or replace the Weekly Planner sheet."""
    if PLANNER_SHEET in wb.sheetnames:
        del wb[PLANNER_SHEET]

    ws = wb.create_sheet(PLANNER_SHEET, 0)   # insert as first sheet

    # ----- Title row -----
    monday = min(buckets.keys())
    friday = max(buckets.keys())
    title = (
        f"📅  Weekly Planner  —  "
        f"{monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}"
    )
    ws.merge_cells(f"A1:{get_column_letter(len(PLANNER_HEADERS))}1")
    title_cell = ws["A1"]
    title_cell.value = title
    title_cell.fill = _fill("1F3864")
    title_cell.font = _font(bold=True, color="FFFFFF", size=14)
    title_cell.alignment = _center()
    ws.row_dimensions[1].height = 28

    # ----- Summary row -----
    total = sum(len(v) for v in buckets.values())
    ws.merge_cells(f"A2:{get_column_letter(len(PLANNER_HEADERS))}2")
    summary_cell = ws["A2"]
    summary_cell.value = (
        f"Auto-transferred {total} high-priority tasks  |  "
        f"Generated: {date.today().strftime('%d %b %Y')}  |  "
        f"Source: {TASKS_SHEET}"
    )
    summary_cell.fill = _fill("2E75B6")
    summary_cell.font = _font(color="FFFFFF", size=10)
    summary_cell.alignment = _center()
    ws.row_dimensions[2].height = 16

    current_row = 4

    for day_date, day_tasks in sorted(buckets.items()):
        day_name = day_date.strftime("%A")

        # Day header
        _write_day_header(ws, current_row, day_name, day_date, len(day_tasks))
        current_row += 1

        # Column headers
        _write_column_headers(ws, current_row, day_name)
        current_row += 1

        # Task rows
        if day_tasks:
            for i, task in enumerate(day_tasks):
                _write_task_row(ws, current_row, task, i)
                current_row += 1
        else:
            ws.merge_cells(
                start_row=current_row, start_column=1,
                end_row=current_row, end_column=len(PLANNER_HEADERS)
            )
            empty_cell = ws.cell(row=current_row, column=1,
                                 value="No tasks scheduled for this day.")
            empty_cell.fill = _fill("F2F2F2")
            empty_cell.font = _font(color="808080", size=10)
            empty_cell.alignment = _center()
            ws.row_dimensions[current_row].height = 22
            current_row += 1

        # Spacer between days
        _write_spacer(ws, current_row)
        current_row += 2

    # ----- Column widths -----
    for col_idx, width in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Freeze top 3 rows
    ws.freeze_panes = "A3"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Auto-transfer priority tasks to a Weekly Planner sheet."
    )
    parser.add_argument(
        "--file", default=DEFAULT_FILE,
        help=f"Path to the Excel workbook (default: {DEFAULT_FILE})"
    )
    parser.add_argument(
        "--week",
        help="ISO date of the Monday to plan for (e.g. 2026-04-06). "
             "Defaults to the current week's Monday."
    )
    args = parser.parse_args()

    # Resolve target week
    if args.week:
        from datetime import datetime
        monday = datetime.strptime(args.week, "%Y-%m-%d").date()
        if monday.weekday() != 0:
            raise ValueError("--week must be a Monday (weekday=0).")
    else:
        monday = current_monday()

    week = week_dates(monday)

    print(f"📂  Loading workbook: {args.file}")
    wb = load_workbook(args.file)

    print(f"📋  Reading tasks from '{TASKS_SHEET}' …")
    tasks = load_tasks(wb)
    print(f"    Found {len(tasks)} high-priority (ABM=YES) tasks.")

    print(f"📅  Planning week: {week[0]} → {week[-1]}")
    buckets = assign_all(tasks, week)

    for d, t in sorted(buckets.items()):
        print(f"    {d.strftime('%A %d %b')}: {len(t):3d} tasks")

    print(f"✏️   Writing '{PLANNER_SHEET}' sheet …")
    build_planner_sheet(wb, buckets)

    wb.save(args.file)
    print(f"✅  Saved: {args.file}")
    print()
    print("Open the workbook and navigate to '📅 Weekly Planner' to see your plan.")


if __name__ == "__main__":
    main()
