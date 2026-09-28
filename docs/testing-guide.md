# Testing guide

Two layers of testing here, matched to what each layer can safely touch.

## 1. Unit tests (no credentials, no SQL Server, no network)

`src/budget_sync/parsing.py` has zero I/O -- it just validates and
normalizes row dicts. `tests/test_parsing.py` covers it with plain
pytest, no mocking needed.

```bash
pip install -e ".[dev]"
pytest -v
```

This is also what `.github/workflows/ci.yml` runs on every push -- it
never needs real SQL Server or Google credentials, so it can't leak
anything and can't fail because a test database is unreachable.

## 2. End-to-end test (real Sheet -> real local SQL Server)

This is the layer that answers "does it read the data correctly and put
it where it needs to go" -- run it before ever pointing `push.py` at
production.

1. **Start the local SQL Server container** (run these from the project
   root, not from inside `docker/` -- the `--env-file` flag is what
   points compose at `.env.test`, since it lives one level up from the
   compose file):
   ```bash
   cp .env.test.example .env.test   # then fill in a real TEST_SQL_SA_PASSWORD
   docker compose -f docker/docker-compose.yml --env-file .env.test up -d
   docker compose -f docker/docker-compose.yml --env-file .env.test logs -f init
   # wait for "Schema + stored procedures loaded."
   ```
2. **Point budget-sync at the TEST COPY sheet**, not the real Master
   Budget Templates sheet. `.env.test.example` already has the TEST COPY's
   sheet ID filled in (`1lcEciNjyUuqI136T-UGys_SpA2UYHKKP_rbeiFpYLTo`).
3. **Get a Google service account key** with at least Viewer access to
   the TEST COPY sheet, save it as `service-account.json` in the project
   root (already gitignored).
4. **Run the push script against the test env:**
   ```bash
   pip install -e .
   python -m budget_sync.push --env-file .env.test
   ```
   Read the preview it prints carefully before answering `y` -- this is
   the same preview-then-confirm step the earlier browser-based tool used,
   just from the command line.
5. **Check the results directly in SQL Server:**
   ```bash
   docker exec -it budget-sync-sqlserver /opt/mssql-tools18/bin/sqlcmd \
     -C -S localhost -U sa -P "$TEST_SQL_SA_PASSWORD" -d BudgetSyncTest \
     -Q "SELECT * FROM dbo.LaborBudget; SELECT * FROM dbo.CensusBudget;"
   ```
6. **Tear down when done** (from the project root again):
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env.test down -v
   # -v also deletes the container's data volume
   ```

## Why this split

Unit tests can run in CI on every commit because they touch nothing
external. The end-to-end test is deliberately manual and local-only --
it writes real rows (to a throwaway local database, using a copy of
the real sheet), so it's the same "you run it, you watch it, you
confirm before it writes" workflow as the production script, just aimed
at a sandbox instead of SQL Server proper.
