"""
Pure parsing/validation logic for Labor and Census budget rows.

Deliberately has zero I/O dependencies (no gspread, no pyodbc) so it can be
unit tested without credentials, a network connection, or the ODBC driver
installed. All Sheets/SQL Server orchestration lives in push.py instead.
"""

from __future__ import annotations

REQUIRED_LABOR_FIELDS = [
    "Org", "FacilityID", "PositionID", "Type", "Input", "StartDate", "EndDate",
]
REQUIRED_CENSUS_FIELDS = [
    "Org", "FacilityID", "PayerType", "Input", "StartDate", "EndDate",
]


def _req(record: dict, key: str) -> str:
    val = (record.get(key) or "").strip()
    if not val:
        raise ValueError(f"missing required field '{key}'")
    return val


def _opt(record: dict, key: str) -> str | None:
    val = (record.get(key) or "").strip()
    return val if val else None


def parse_labor_row(record: dict) -> dict:
    """Validate and normalize one row from the Labor Budget Template tab.

    `record` is a dict keyed by column header (as returned by
    gspread's `get_all_records()`). Raises ValueError with a message
    naming the missing/invalid field if the row is not usable.
    """
    parsed = {
        "id": _opt(record, "ID"),
        "org": _req(record, "Org"),
        "facility_id": _req(record, "FacilityID"),
        "facility_code": _opt(record, "FacilityCode"),
        "position_id": _req(record, "PositionID"),
        "position_name": _opt(record, "PositionName"),
        "type": _req(record, "Type"),
        "input": _req(record, "Input"),
        "wage_amount": _opt(record, "WageAmount"),
        "weekend_work": _opt(record, "WeekendWork"),
        "start_date": _req(record, "StartDate"),
        "end_date": _req(record, "EndDate"),
        "alt_ppd_input": _opt(record, "AltPPDInput"),
    }

    if parsed["type"].upper() not in ("HPPD", "FTE"):
        raise ValueError(f"Type must be 'HPPD' or 'FTE', got '{parsed['type']}'")

    try:
        float(parsed["input"])
    except ValueError:
        raise ValueError(f"Input must be numeric, got '{parsed['input']}'")

    return parsed


def parse_census_row(record: dict) -> dict:
    """Validate and normalize one row from the Census Budget Template tab."""
    parsed = {
        "id": _opt(record, "ID"),
        "org": _req(record, "Org"),
        "facility_id": _req(record, "FacilityID"),
        "facility_code": _opt(record, "FacilityCode"),
        "payer_type": _req(record, "PayerType"),
        "input": _req(record, "Input"),
        "start_date": _req(record, "StartDate"),
        "end_date": _req(record, "EndDate"),
    }

    try:
        float(parsed["input"])
    except ValueError:
        raise ValueError(f"Input must be numeric, got '{parsed['input']}'")

    return parsed


def is_blank_row(row: list) -> bool:
    """True if every cell in a raw row (list of strings) is empty/whitespace."""
    return all((cell or "").strip() == "" for cell in row)


def build_preview(kind: str, parsed_rows: list[dict]) -> str:
    """Human-readable summary of what would be inserted/updated, for the
    confirmation prompt before anything is written to SQL Server."""
    lines = [f"{kind.upper()} BUDGET -- {len(parsed_rows)} row(s) to push:"]
    for row in parsed_rows:
        action = "UPDATE" if row.get("id") else "INSERT"
        if kind == "labor":
            lines.append(
                f"  {action} FacilityID={row['facility_id']} "
                f"PositionID={row['position_id']} Type={row['type']} "
                f"Input={row['input']} ({row['start_date']} to {row['end_date']})"
            )
        else:
            lines.append(
                f"  {action} FacilityID={row['facility_id']} "
                f"PayerType={row['payer_type']} Input={row['input']} "
                f"({row['start_date']} to {row['end_date']})"
            )
    return "\n".join(lines)
