-- ============================================================
-- usp_UpsertCensusBudget
-- ------------------------------------------------------------
-- Same insert/update convention as usp_UpsertLaborBudget:
--   * @ID = NULL  -> insert a new row
--   * @ID = existing row -> update it
--   * @ID = something that doesn't exist -> error, not a silent insert
--
-- Adjust the table name (dbo.CensusBudget) and column names/types
-- below to match your actual table before running this.
-- ============================================================
CREATE OR ALTER PROCEDURE dbo.usp_UpsertCensusBudget
    @ID           INT = NULL,
    @Org          VARCHAR(20),
    @FacilityID   INT,
    @FacilityCode VARCHAR(20)  = NULL,
    @PayerType    VARCHAR(50),
    @Input        DECIMAL(10,2),
    @StartDate    DATE,
    @EndDate      DATE
AS
BEGIN
    SET NOCOUNT ON;

    IF @ID IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.CensusBudget WHERE ID = @ID)
    BEGIN
        RAISERROR('CensusBudget.ID %d not found -- refusing to insert an orphaned ID. Leave ID blank for a new row.', 16, 1, @ID);
        RETURN;
    END

    DECLARE @ResultID INT;

    IF @ID IS NOT NULL
    BEGIN
        UPDATE dbo.CensusBudget
        SET Org          = @Org,
            FacilityID   = @FacilityID,
            FacilityCode = @FacilityCode,
            PayerType    = @PayerType,
            Input        = @Input,
            StartDate    = @StartDate,
            EndDate      = @EndDate
        WHERE ID = @ID;

        SET @ResultID = @ID;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.CensusBudget (Org, FacilityID, FacilityCode, PayerType, Input, StartDate, EndDate)
        VALUES (@Org, @FacilityID, @FacilityCode, @PayerType, @Input, @StartDate, @EndDate);

        SET @ResultID = SCOPE_IDENTITY();
    END

    SELECT @ResultID AS ResultID;
END
GO
