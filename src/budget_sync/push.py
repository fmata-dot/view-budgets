"""
Sheets -> SQL Server orchestration for budget-sync.

Reads the Labor Budget Template and Census Budget Template tabs from the
Master Budget Templates Google Sheet, validates each row (parsing.py),
shows a preview, and -- once confirmed -- pushes rows one at a time to
SQL Server via the usp_UpsertLaborBudget / usp_UpsertCensusBudget stored
procedures.

Run manually:
    python -m budget_sync.push            # prompts y/N before writing
    python -m budget_sync.push --yes       # skips the confirmation prompt
    python -m budget_sync.push --env-file .env.test   # point at test env
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from budget_sync.parsing import (
    build_preview,
    is_blank_row,
    parse_census_row,
    parse_labor_row,
)

LABOR_TAB = "Labor Budget Template"
CENSUS_TAB = "Census Budget Template"
HEADER_ROW = 2  # row 1 = instructional notes, row 2 = real column headers


def get_sheet_records(sheet_id: str, tab_name: str):
    """Read a tab's rows as a list of dicts keyed by column header.

    Uses a read-only service account -- this script never writes back to
    the Google Sheet, only to SQL Server.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    creds_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(tab_name)
    return worksheet.get_all_records(head=HEADER_ROW)


def get_sql_connection():
    import pyodbc

    server = os.environ["SQL_SERVER"]
    database = os.environ["SQL_DATABASE"]
    user = os.environ["SQL_USER"]
    password = os.environ["SQL_PASSWORD"]

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str)


def push_labor_row(conn, row: dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "{CALL dbo.usp_UpsertLaborBudget "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?)}",
        row.get("id"),
        row["org"],
        row["facility_id"],
        row.get("facility_code"),
        row["position_id"],
        row["type"],
        row["input"],
        row.get("wage_amount"),
        row.get("weekend_work"),
        row["start_date"],
        row["end_date"],
        row.get("position_name"),
        row.get("alt_ppd_input"),
    )
    result = cursor.fetchone()
    conn.commit()
    return result.ResultID if result else None


def push_census_row(conn, row: dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "{CALL dbo.usp_UpsertCensusBudget (?,?,?,?,?,?,?,?)}",
        row.get("id"),
        row["org"],
        row["facility_id"],
        row.get("facility_code"),
        row["payer_type"],
        row["input"],
        row["start_date"],
        row["end_date"],
    )
    result = cursor.fetchone()
    conn.commit()
    return result.ResultID if result else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--env-file", default=".env", help="which env file to load (default: .env)")
    args = parser.parse_args(argv)

    load_dotenv(args.env_file)
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    labor_records = get_sheet_records(sheet_id, LABOR_TAB)
    census_records = get_sheet_records(sheet_id, CENSUS_TAB)

    labor_rows, labor_errors = [], []
    for i, record in enumerate(labor_records, start=HEADER_ROW + 1):
        if is_blank_row(list(record.values())):
            continue
        try:
            labor_rows.append(parse_labor_row(record))
        except ValueError as e:
            labor_errors.append(f"  row {i}: {e}")

    census_rows, census_errors = [], []
    for i, record in enumerate(census_records, start=HEADER_ROW + 1):
        if is_blank_row(list(record.values())):
            continue
        try:
            census_rows.append(parse_census_row(record))
        except ValueError as e:
            census_errors.append(f"  row {i}: {e}")

    if labor_errors:
        print(f"Skipping {len(labor_errors)} invalid Labor row(s):")
        print("\n".join(labor_errors))
    if census_errors:
        print(f"Skipping {len(census_errors)} invalid Census row(s):")
        print("\n".join(census_errors))

    if not labor_rows and not census_rows:
        print("Nothing valid to push. Exiting.")
        return 0

    print()
    print(build_preview("labor", labor_rows))
    print()
    print(build_preview("census", census_rows))
    print()

    if not args.yes:
        answer = input("Push these changes to SQL Server? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted, nothing written.")
            return 0

    conn = get_sql_connection()
    ok, failed = 0, 0
    for row in labor_rows:
        try:
            push_labor_row(conn, row)
            ok += 1
        except Exception as e:
            failed += 1
            print(f"FAIL (labor, FacilityID={row['facility_id']}): {e}")
    for row in census_rows:
        try:
            push_census_row(conn, row)
            ok += 1
        except Exception as e:
            failed += 1
            print(f"FAIL (census, FacilityID={row['facility_id']}): {e}")
    conn.close()

    print(f"\nDone. {ok} succeeded, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
