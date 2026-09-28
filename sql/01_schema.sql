-- Run against BudgetSyncTest (or your target database).
-- Minimal table definitions matching the Master Budget Templates columns,
-- enough to exercise the upsert stored procedures end-to-end in the test
-- environment. Column types are a reasonable first pass -- confirm against
-- the real CovrHub schema before using this against production.

USE BudgetSyncTest;
GO

IF OBJECT_ID('dbo.LaborBudget', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.LaborBudget (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Org             NVARCHAR(50)    NOT NULL,
        FacilityID      NVARCHAR(50)    NOT NULL,
        FacilityCode    NVARCHAR(50)    NULL,
        PositionID      NVARCHAR(50)    NOT NULL,
        PositionName    NVARCHAR(200)   NULL,
        Type            NVARCHAR(10)    NOT NULL,   -- 'HPPD' or 'FTE'
        Input           DECIMAL(10,2)   NOT NULL,
        WageAmount      DECIMAL(10,2)   NULL,
        WeekendWork     NVARCHAR(5)     NULL,
        StartDate       DATE            NOT NULL,
        EndDate         DATE            NOT NULL,
        AltPPDInput     DECIMAL(10,2)   NULL,
        CreatedAt       DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
        UpdatedAt       DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

IF OBJECT_ID('dbo.CensusBudget', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.CensusBudget (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Org             NVARCHAR(50)    NOT NULL,
        FacilityID      NVARCHAR(50)    NOT NULL,
        FacilityCode    NVARCHAR(50)    NULL,
        PayerType       NVARCHAR(100)   NOT NULL,
        Input           DECIMAL(10,2)   NOT NULL,
        StartDate       DATE            NOT NULL,
        EndDate         DATE            NOT NULL,
        CreatedAt       DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
        UpdatedAt       DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO
