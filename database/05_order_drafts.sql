SET XACT_ABORT ON;
IF OBJECT_ID(N'dbo.OrderDrafts',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.OrderDrafts (
        DraftID int IDENTITY(1,1) NOT NULL CONSTRAINT PK_OrderDrafts PRIMARY KEY,
        DraftKey varchar(36) NOT NULL CONSTRAINT UQ_OrderDrafts_Key UNIQUE,
        UserID int NOT NULL CONSTRAINT FK_OrderDrafts_Users REFERENCES dbo.Users(UserID),
        Payload nvarchar(max) NOT NULL,
        Step tinyint NOT NULL CONSTRAINT DF_OrderDrafts_Step DEFAULT(0),
        Revision int NOT NULL CONSTRAINT DF_OrderDrafts_Revision DEFAULT(1),
        UpdatedAt datetime2(0) NOT NULL CONSTRAINT DF_OrderDrafts_Updated DEFAULT(SYSUTCDATETIME()),
        SubmittedOrderID int NULL CONSTRAINT FK_OrderDrafts_Orders REFERENCES dbo.Orders(OrderID),
        CONSTRAINT CK_OrderDrafts_JSON CHECK(ISJSON(Payload)=1),
        CONSTRAINT CK_OrderDrafts_Step CHECK(Step BETWEEN 0 AND 3),
        CONSTRAINT CK_OrderDrafts_Revision CHECK(Revision>0)
    );
    CREATE UNIQUE INDEX UX_OrderDrafts_ActiveUser ON dbo.OrderDrafts(UserID) WHERE SubmittedOrderID IS NULL;
END;
GO
