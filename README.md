# budget-sync

Pushes labor and census budget numbers from a Google Sheet into SQL
Server, replacing a manual copy/paste step.

## What it does

Covr tracks facility staffing and census budgets in a shared Google
Sheet (Master Budget Templates). Today, getting those numbers into SQL
Server means copying rows out of the sheet and pasting them into a
database query by hand.

This tool automates that copy/paste: it reads the sheet, checks each
row for problems, shows a preview of exactly what will change, and —
only once a person confirms — writes the rows to SQL Server.

## How it works

- **Manual, not automatic.** It's a script someone runs on purpose. It
  doesn't run on a schedule and doesn't touch anything until a person
  types `y` at the confirmation prompt.
- **Read-only on the sheet.** It only reads from Google Sheets, never
  writes back to it.
- **Safe by design on SQL Server.** Two stored procedures handle the
  actual writes: a blank ID means "insert a new row," an existing ID
  means "update that row," and an unrecognized ID is rejected with an
  error instead of silently creating a duplicate or corrupting data.

## Repo layout

| Folder | What's in it |
|---|---|
| `sql/` | Table definitions and the two stored procedures that do the actual writing |
| `src/budget_sync/` | The Python code: row validation logic, and the script that ties it all together |
| `tests/` | Automated tests for the validation logic (12 tests, run on every push via GitHub Actions) |
| `docker/` | A disposable local SQL Server, for testing without touching the real database |
| `docs/` | Setup instructions and a testing walkthrough |

## Getting started

See [`docs/setup-guide.md`](docs/setup-guide.md) for installation and
configuration, and [`docs/testing-guide.md`](docs/testing-guide.md) for
how to test it safely before pointing it at real data.
