-- Run this first, against the `master` database.
-- Creates the local test database used by docker-compose / the test env.
-- (In production this step doesn't apply -- you'd point SQL_DATABASE at
-- the real CovrHub database instead.)

IF DB_ID('BudgetSyncTest') IS NULL
BEGIN
    CREATE DATABASE BudgetSyncTest;
END
GO
