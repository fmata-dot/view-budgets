"""
Pure parsing/preview logic for push_budgets_to_sql.py.

No I/O here on purpose (no Google Sheets, no SQL Server, no env
vars) -- this module only turns raw sheet rows (dicts of strings)
into typed dicts, or raises ValueError with a clear message. That
makes it possible to unit test the actual logic without needing
pyodbc, gspread, or a real database anywhere nearby.
"""


def _req(record, key):
    val = (record.get(key) or "").strip()
    if not val:
        raise ValueError(f"missing required field '{key}'")
    return val


def _opt(record, key):
    val = (record.get(key) or "").strip()
    return val if val else None


def parse_labor_row(record):
    """record: dict mapping column header -> raw string cell value
    (as read straight from the sheet). Returns a typed dict ready to
    pass to usp_UpsertLaborBudget, or raises ValueError."""
    budget_type = _req(record, "Type").upper()
    if budget_type not in ("HPPD", "FTE"):
        raise ValueError(f"Type must be HPPD or FTE, got '{budget_type}'")

    raw_id = _opt(record, "ID")
    alt_ppd = _opt(record, "AltPPDInput")
    wage = _opt(record, "WageAmount")
    weekend_raw = (record.get("WeekendWork") or "").strip().lower()

    return {
        "id": int(raw_id) if raw_id else None,
        "org": _req(record, "Org"),
        "facility_id": int(_req(record, "FacilityID")),
        "facility_code": _opt(record, "FacilityCode"),
        "position_id": int(_req(record, "PositionID")),
        "type": budget_type,
        "input": float(_req(record, "Input")),
        "alt_ppd_input": float(alt_ppd) if alt_ppd else None,
        "wage_amount": float(wage) if wage else None,
        "weekend_work": weekend_raw in ("1", "yes", "y", "true"),
        "start_date": _req(record, "StartDate"),
        "end_date": _req(record, "EndDate"),
        "position_name": _opt(record, "PositionName"),
    }


def parse_census_row(record):
    raw_id = _opt(record, "ID")
    return {
        "id": int(raw_id) if raw_id else None,
        "org": _req(record, "Org"),
        "facility_id": int(_req(record, "FacilityID")),
        "facility_code": _opt(record, "FacilityCode"),
        "payer_type": _req(record, "PayerType"),
        "input": float(_req(record, "Input")),
        "start_date": _req(record, "StartDate"),
        "end_date": _req(record, "EndDate"),
    }


def is_blank_row(row):
    """row: list of raw string cell values for one sheet row."""
    return not any(cell.strip() for cell in row)


def build_preview(kind, parsed_rows):
    lines = [f"{len(parsed_rows)} {kind} row(s) to push:"]
    for i, row in enumerate(parsed_rows, start=1):
        action = f"UPDATE #{row['id']}" if row["id"] else "INSERT (new)"
        if kind == "labor":
            lines.append(
                f"  {i}. {action} -- Facility {row['facility_id']}, Position {row['position_id']}, "
                f"{row['type']} {row['input']}, {row['start_date']} to {row['end_date']}"
            )
        else:
            lines.append(
                f"  {i}. {action} -- Facility {row['facility_id']}, {row['payer_type']} {row['input']}, "
                f"{row['start_date']} to {row['end_date']}"
            )
    return "\n".join(lines)
