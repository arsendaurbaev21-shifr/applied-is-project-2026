-- Additive, repeatable migration. Run on QazCargo; never drops user data.
SET XACT_ABORT ON;
IF OBJECT_ID(N'dbo.Orders',N'U') IS NULL OR OBJECT_ID(N'dbo.Users',N'U') IS NULL
 THROW 51100,'Install the base QazCargo schema first.',1;
IF COL_LENGTH('dbo.Orders','SenderName') IS NULL
 ALTER TABLE dbo.Orders ADD SenderName nvarchar(120) NULL,SenderPhone nvarchar(30) NULL,
 PickupAddress nvarchar(250) NULL,RecipientName nvarchar(120) NULL,RecipientPhone nvarchar(30) NULL,
 DeliveryAddress nvarchar(250) NULL,PickupWindowStart time(0) NULL,PickupWindowEnd time(0) NULL;
IF COL_LENGTH('dbo.Orders','TrackingCode') IS NULL
 ALTER TABLE dbo.Orders ADD TrackingCode varchar(64) NOT NULL
 CONSTRAINT DF_Orders_TrackingCode DEFAULT (CONVERT(varchar(64),CRYPT_GEN_RANDOM(32),2)) WITH VALUES;
GO
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name='CK_Orders_PickupWindow')
 ALTER TABLE dbo.Orders ADD CONSTRAINT CK_Orders_PickupWindow CHECK
 ((PickupWindowStart IS NULL AND PickupWindowEnd IS NULL) OR
 (PickupWindowStart IS NOT NULL AND PickupWindowEnd IS NOT NULL AND PickupWindowEnd>PickupWindowStart));
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='UX_Orders_TrackingCode')
 CREATE UNIQUE INDEX UX_Orders_TrackingCode ON dbo.Orders(TrackingCode);
IF OBJECT_ID(N'dbo.Notifications',N'U') IS NULL
BEGIN
 CREATE TABLE dbo.Notifications(
  NotificationID int IDENTITY(1,1) CONSTRAINT PK_Notifications PRIMARY KEY,
  UserID int NOT NULL CONSTRAINT FK_Notifications_Users REFERENCES dbo.Users(UserID),
  OrderID int NOT NULL CONSTRAINT FK_Notifications_Orders REFERENCES dbo.Orders(OrderID),
  EventType varchar(30) NOT NULL,
  NewStatus nvarchar(20) NULL,
  CreatedAt datetime2(0) NOT NULL CONSTRAINT DF_Notifications_Created DEFAULT SYSUTCDATETIME(),
  ReadAt datetime2(0) NULL,
  CONSTRAINT CK_Notifications_Type CHECK(EventType IN('order_created','status_changed','trip_updated','delivery_updated')),
  CONSTRAINT CK_Notifications_Status CHECK(NewStatus IS NULL OR NewStatus IN('New','Confirmed','InTransit','Delivered','Cancelled'))
 );
 CREATE INDEX IX_Notifications_UserRead ON dbo.Notifications(UserID,ReadAt,NotificationID DESC);
 CREATE INDEX IX_Notifications_Order ON dbo.Notifications(OrderID);
END;
