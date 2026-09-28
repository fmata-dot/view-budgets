-- ============================================================
-- usp_UpsertLaborBudget
-- ------------------------------------------------------------
-- Insert a new labor budget row, or update an existing one.
--   * Pass @ID = NULL to insert a new row (matches the sheet's
--     "leave ID blank for a new row" convention).
--   * Pass an existing @ID to update that row.
--   * Passing an @ID that doesn't exist raises an error instead
--     of silently inserting an orphaned row (protects against a
--     typo'd ID creating a duplicate rather than updating the
--     row you meant).
--
-- Adjust the table name (dbo.LaborBudget) and column names/types
-- below to match your actual table before running this.
-- ============================================================
CREATE OR ALTER PROCEDURE dbo.usp_UpsertLaborBudget
    @ID           INT = NULL,
    @Org          VARCHAR(20),
    @FacilityID   INT,
    @FacilityCode VARCHAR(20)   = NULL,
    @PositionID   INT,
    @Type         VARCHAR(10),          -- 'HPPD' or 'FTE'
    @Input        DECIMAL(10,4),
    @AltPPDInput  DECIMAL(10,4) = NULL,
    @WageAmount   DECIMAL(10,2) = NULL,
    @WeekendWork  BIT           = 0,
    @StartDate    DATE,
    @EndDate      DATE,
    @PositionName VARCHAR(200)  = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @Type NOT IN ('HPPD', 'FTE')
    BEGIN
        RAISERROR('Type must be ''HPPD'' or ''FTE'', got ''%s''.', 16, 1, @Type);
        RETURN;
    END

    IF @ID IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.LaborBudget WHERE ID = @ID)
    BEGIN
        RAISERROR('LaborBudget.ID %d not found -- refusing to insert an orphaned ID. Leave ID blank for a new row.', 16, 1, @ID);
        RETURN;
    END

    DECLARE @ResultID INT;

    IF @ID IS NOT NULL
    BEGIN
        UPDATE dbo.LaborBudget
        SET Org          = @Org,
            FacilityID   = @FacilityID,
            FacilityCode = @FacilityCode,
            PositionID   = @PositionID,
            Type         = @Type,
            Input        = @Input,
            AltPPDInput  = @AltPPDInput,
            WageAmount   = @WageAmount,
            WeekendWork  = @WeekendWork,
            StartDate    = @StartDate,
            EndDate      = @EndDate,
            PositionName = @PositionName
        WHERE ID = @ID;

        SET @ResultID = @ID;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.LaborBudget
            (Org, FacilityID, FacilityCode, PositionID, Type, Input, AltPPDInput, WageAmount, WeekendWork, StartDate, EndDate, PositionName)
        VALUES
            (@Org, @FacilityID, @FacilityCode, @PositionID, @Type, @Input, @AltPPDInput, @WageAmount, @WeekendWork, @StartDate, @EndDate, @PositionName);

        SET @ResultID = SCOPE_IDENTITY();
    END

    -- Returned as a normal result set (not an OUTPUT param) so any
    -- client library -- pyodbc, SSMS, Postman-via-API, etc. -- can
    -- read it back the same simple way.
    SELECT @ResultID AS ResultID;
END
GO
