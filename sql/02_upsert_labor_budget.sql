-- Upsert stored procedure for the Labor Budget table.
-- Convention: blank/NULL @ID = insert a new row (ID assigned by SCOPE_IDENTITY());
-- a non-NULL @ID that doesn't exist is rejected (RAISERROR) rather than silently
-- inserting or ignoring -- catches typos/stale IDs instead of masking them.
-- Explicit IF EXISTS / UPDATE / INSERT branching is used instead of MERGE:
-- MERGE has known edge-case bugs and locking behavior that make explicit
-- branching the safer choice for this kind of low-volume, high-stakes write.

USE BudgetSyncTest;
GO

CREATE OR ALTER PROCEDURE dbo.usp_UpsertLaborBudget
    @ID             INT = NULL,
    @Org            NVARCHAR(50),
    @FacilityID     NVARCHAR(50),
    @FacilityCode   NVARCHAR(50) = NULL,
    @PositionID     NVARCHAR(50),
    @Type           NVARCHAR(10),
    @Input          DECIMAL(10,2),
    @WageAmount     DECIMAL(10,2) = NULL,
    @WeekendWork    NVARCHAR(5) = NULL,
    @StartDate      DATE,
    @EndDate        DATE,
    @PositionName   NVARCHAR(200) = NULL,
    @AltPPDInput    DECIMAL(10,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ResultID INT;

    IF @ID IS NOT NULL
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.LaborBudget WHERE ID = @ID)
        BEGIN
            RAISERROR('LaborBudget.ID %d does not exist -- refusing to insert with an explicit but unknown ID.', 16, 1, @ID);
            RETURN;
        END

        UPDATE dbo.LaborBudget
        SET Org = @Org,
            FacilityID = @FacilityID,
            FacilityCode = @FacilityCode,
            PositionID = @PositionID,
            PositionName = @PositionName,
            Type = @Type,
            Input = @Input,
            WageAmount = @WageAmount,
            WeekendWork = @WeekendWork,
            StartDate = @StartDate,
            EndDate = @EndDate,
            AltPPDInput = @AltPPDInput,
            UpdatedAt = SYSUTCDATETIME()
        WHERE ID = @ID;

        SET @ResultID = @ID;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.LaborBudget
            (Org, FacilityID, FacilityCode, PositionID, PositionName, Type,
             Input, WageAmount, WeekendWork, StartDate, EndDate, AltPPDInput)
        VALUES
            (@Org, @FacilityID, @FacilityCode, @PositionID, @PositionName, @Type,
             @Input, @WageAmount, @WeekendWork, @StartDate, @EndDate, @AltPPDInput);

        SET @ResultID = SCOPE_IDENTITY();
    END

    SELECT @ResultID AS ResultID;
END
GO
