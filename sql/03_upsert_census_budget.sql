-- Upsert stored procedure for the Census Budget table.
-- Same insert/update convention as usp_UpsertLaborBudget -- see that file
-- for the reasoning (blank ID = insert, unknown explicit ID = rejected).

USE BudgetSyncTest;
GO

CREATE OR ALTER PROCEDURE dbo.usp_UpsertCensusBudget
    @ID             INT = NULL,
    @Org            NVARCHAR(50),
    @FacilityID     NVARCHAR(50),
    @FacilityCode   NVARCHAR(50) = NULL,
    @PayerType      NVARCHAR(100),
    @Input          DECIMAL(10,2),
    @StartDate      DATE,
    @EndDate        DATE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ResultID INT;

    IF @ID IS NOT NULL
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.CensusBudget WHERE ID = @ID)
        BEGIN
            RAISERROR('CensusBudget.ID %d does not exist -- refusing to insert with an explicit but unknown ID.', 16, 1, @ID);
            RETURN;
        END

        UPDATE dbo.CensusBudget
        SET Org = @Org,
            FacilityID = @FacilityID,
            FacilityCode = @FacilityCode,
            PayerType = @PayerType,
            Input = @Input,
            StartDate = @StartDate,
            EndDate = @EndDate,
            UpdatedAt = SYSUTCDATETIME()
        WHERE ID = @ID;

        SET @ResultID = @ID;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.CensusBudget
            (Org, FacilityID, FacilityCode, PayerType, Input, StartDate, EndDate)
        VALUES
            (@Org, @FacilityID, @FacilityCode, @PayerType, @Input, @StartDate, @EndDate);

        SET @ResultID = SCOPE_IDENTITY();
    END

    SELECT @ResultID AS ResultID;
END
GO
