/* QazCargo 3 — жаңа сервер/интерфейске арналған тексерілген 17 кестелік схема.
   Бастапқы DDL: пайдаланушы берген v2 үлгісі; түзетілген тұтастық, уақыт, индекстер және VIEW.
   SQL Server 2016+ (SSMS 22 — клиенттік редактор). SQLCMD режимі қажет емес.
   FIRST_RUN.bat орнатқышы 01 және 02 файлдарын ретімен орындайды. UTF-8 файлды SSMS-те ашыңыз.
   БАР ДЕРЕКҚОР ЖОЙЫЛМАЙДЫ: егер QazCargo бар болса, бүкіл DDL бөлігі бұғатталады.
   Session marker protects later GO batches even if SSMS continues after THROW.
   No DROP DATABASE, DELETE reset, TRUNCATE, or cascading delete.
*/
USE master;
GO
SET NOCOUNT ON;
EXEC sys.sp_set_session_context @key=N'QazCargo.CreateAuthorized',@value=NULL;
IF DB_ID(N'QazCargo') IS NOT NULL
 THROW 51000,N'QazCargo базасы бұрыннан бар. Құру тоқтатылды; деректер өзгерген жоқ.',1;
EXEC(N'CREATE DATABASE QazCargo');
EXEC sys.sp_set_session_context @key=N'QazCargo.CreateAuthorized',@value=1;
GO
USE QazCargo;
GO
IF COALESCE(TRY_CONVERT(INT,SESSION_CONTEXT(N'QazCargo.CreateAuthorized')),0)<>1
 THROW 51000,N'Жаңа базаны құруға осы сессияда рұқсат жоқ; барлық DDL тоқтатылды.',1;
SET NOCOUNT ON; SET XACT_ABORT ON; SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
BEGIN TRY
 BEGIN TRANSACTION;

CREATE TABLE dbo.Clients (
 ClientID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Clients PRIMARY KEY,
 Name NVARCHAR(120) NOT NULL, Phone NVARCHAR(30) NOT NULL, Email NVARCHAR(120) NULL,
 Address NVARCHAR(250) NULL, CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Clients_CreatedAt DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_Clients_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0), CONSTRAINT CK_Clients_Phone CHECK(LEN(LTRIM(RTRIM(Phone)))>0)
);
CREATE TABLE dbo.Cities (
 CityID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Cities PRIMARY KEY, Name NVARCHAR(80) NOT NULL CONSTRAINT UQ_Cities_Name UNIQUE,
 CONSTRAINT CK_Cities_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)
);
CREATE TABLE dbo.VehicleTypes (
 VehicleTypeID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_VehicleTypes PRIMARY KEY, Name NVARCHAR(60) NOT NULL CONSTRAINT UQ_VehicleTypes_Name UNIQUE,
 CONSTRAINT CK_VehicleTypes_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)
);
CREATE TABLE dbo.Vehicles (
 VehicleID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Vehicles PRIMARY KEY, VehicleTypeID INT NOT NULL,
 PlateNumber NVARCHAR(20) NOT NULL CONSTRAINT UQ_Vehicles_PlateNumber UNIQUE, Brand NVARCHAR(80) NOT NULL,
 CapacityKg DECIMAL(12,2) NOT NULL, IsActive BIT NOT NULL CONSTRAINT DF_Vehicles_IsActive DEFAULT 1,
 CONSTRAINT FK_Vehicles_VehicleTypes FOREIGN KEY(VehicleTypeID) REFERENCES dbo.VehicleTypes(VehicleTypeID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Vehicles_Capacity CHECK(CapacityKg>0), CONSTRAINT CK_Vehicles_Plate CHECK(LEN(LTRIM(RTRIM(PlateNumber)))>0), CONSTRAINT CK_Vehicles_Brand CHECK(LEN(LTRIM(RTRIM(Brand)))>0)
);
CREATE TABLE dbo.Drivers (
 DriverID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Drivers PRIMARY KEY, FullName NVARCHAR(120) NOT NULL, Phone NVARCHAR(30) NOT NULL,
 LicenseNumber NVARCHAR(30) NOT NULL CONSTRAINT UQ_Drivers_LicenseNumber UNIQUE, IsActive BIT NOT NULL CONSTRAINT DF_Drivers_IsActive DEFAULT 1,
 CONSTRAINT CK_Drivers_Name CHECK(LEN(LTRIM(RTRIM(FullName)))>0), CONSTRAINT CK_Drivers_Phone CHECK(LEN(LTRIM(RTRIM(Phone)))>0), CONSTRAINT CK_Drivers_License CHECK(LEN(LTRIM(RTRIM(LicenseNumber)))>0)
);
CREATE TABLE dbo.Routes (
 RouteID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Routes PRIMARY KEY, FromCityID INT NOT NULL, ToCityID INT NOT NULL, DistanceKm DECIMAL(10,2) NOT NULL,
 CONSTRAINT FK_Routes_FromCity FOREIGN KEY(FromCityID) REFERENCES dbo.Cities(CityID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_Routes_ToCity FOREIGN KEY(ToCityID) REFERENCES dbo.Cities(CityID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Routes_DifferentCities CHECK(FromCityID<>ToCityID), CONSTRAINT CK_Routes_Distance CHECK(DistanceKm>0), CONSTRAINT UQ_Routes_CityPair UNIQUE(FromCityID,ToCityID)
);
CREATE TABLE dbo.CargoTypes (
 CargoTypeID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_CargoTypes PRIMARY KEY, Name NVARCHAR(80) NOT NULL CONSTRAINT UQ_CargoTypes_Name UNIQUE, Description NVARCHAR(250) NULL,
 CONSTRAINT CK_CargoTypes_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)
);
CREATE TABLE dbo.Tariffs (
 TariffID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Tariffs PRIMARY KEY, Name NVARCHAR(100) NOT NULL, VehicleTypeID INT NOT NULL,
 BasePrice DECIMAL(14,2) NOT NULL, PricePerKm DECIMAL(12,2) NOT NULL, PricePerKg DECIMAL(12,2) NOT NULL,
 IsActive BIT NOT NULL CONSTRAINT DF_Tariffs_IsActive DEFAULT 1,
 CONSTRAINT FK_Tariffs_VehicleTypes FOREIGN KEY(VehicleTypeID) REFERENCES dbo.VehicleTypes(VehicleTypeID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Tariffs_Prices CHECK(BasePrice>=0 AND PricePerKm>=0 AND PricePerKg>=0), CONSTRAINT CK_Tariffs_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)
);
CREATE TABLE dbo.Orders (
 OrderID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Orders PRIMARY KEY, OrderNumber NVARCHAR(30) NOT NULL CONSTRAINT UQ_Orders_OrderNumber UNIQUE,
 ClientID INT NOT NULL, RouteID INT NOT NULL, TariffID INT NOT NULL,
 OrderDate DATETIME2(0) NOT NULL CONSTRAINT DF_Orders_OrderDate DEFAULT SYSUTCDATETIME(), PickupDate DATE NOT NULL,
 Status NVARCHAR(20) NOT NULL CONSTRAINT DF_Orders_Status DEFAULT N'New', Notes NVARCHAR(500) NULL,
 QuotedAmount DECIMAL(14,2) NOT NULL CONSTRAINT DF_Orders_QuotedAmount DEFAULT 0,
 CONSTRAINT FK_Orders_Clients FOREIGN KEY(ClientID) REFERENCES dbo.Clients(ClientID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_Orders_Routes FOREIGN KEY(RouteID) REFERENCES dbo.Routes(RouteID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_Orders_Tariffs FOREIGN KEY(TariffID) REFERENCES dbo.Tariffs(TariffID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Orders_Status CHECK(Status IN(N'New',N'Confirmed',N'InTransit',N'Delivered',N'Cancelled')),
 CONSTRAINT CK_Orders_Quote CHECK(QuotedAmount>=0), CONSTRAINT CK_Orders_Number CHECK(LEN(LTRIM(RTRIM(OrderNumber)))>0)
);
CREATE TABLE dbo.CargoItems (
 CargoItemID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_CargoItems PRIMARY KEY, OrderID INT NOT NULL, CargoTypeID INT NOT NULL,
 Description NVARCHAR(200) NOT NULL, WeightKg DECIMAL(12,2) NOT NULL, VolumeM3 DECIMAL(12,3) NOT NULL, Quantity INT NOT NULL,
 CONSTRAINT FK_CargoItems_Orders FOREIGN KEY(OrderID) REFERENCES dbo.Orders(OrderID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_CargoItems_CargoTypes FOREIGN KEY(CargoTypeID) REFERENCES dbo.CargoTypes(CargoTypeID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_CargoItems_Weight CHECK(WeightKg>0), CONSTRAINT CK_CargoItems_Volume CHECK(VolumeM3>0), CONSTRAINT CK_CargoItems_Quantity CHECK(Quantity>0),
 CONSTRAINT CK_CargoItems_Description CHECK(LEN(LTRIM(RTRIM(Description)))>0)
);
CREATE TABLE dbo.Trips (
 TripID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Trips PRIMARY KEY, OrderID INT NOT NULL CONSTRAINT UQ_Trips_OrderID UNIQUE,
 VehicleID INT NOT NULL, DriverID INT NOT NULL, DepartureAt DATETIME2(0) NOT NULL, ArrivalAt DATETIME2(0) NOT NULL,
 Status NVARCHAR(20) NOT NULL CONSTRAINT DF_Trips_Status DEFAULT N'Planned',
 CONSTRAINT FK_Trips_Orders FOREIGN KEY(OrderID) REFERENCES dbo.Orders(OrderID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_Trips_Vehicles FOREIGN KEY(VehicleID) REFERENCES dbo.Vehicles(VehicleID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT FK_Trips_Drivers FOREIGN KEY(DriverID) REFERENCES dbo.Drivers(DriverID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Trips_Time CHECK(ArrivalAt>DepartureAt), CONSTRAINT CK_Trips_Status CHECK(Status IN(N'Planned',N'InTransit',N'Completed',N'Cancelled'))
);
CREATE TABLE dbo.Payments (
 PaymentID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Payments PRIMARY KEY, OrderID INT NOT NULL, Amount DECIMAL(14,2) NOT NULL,
 PaidAt DATETIME2(0) NOT NULL CONSTRAINT DF_Payments_PaidAt DEFAULT SYSUTCDATETIME(), Method NVARCHAR(20) NOT NULL, Note NVARCHAR(250) NULL,
 CONSTRAINT FK_Payments_Orders FOREIGN KEY(OrderID) REFERENCES dbo.Orders(OrderID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_Payments_Amount CHECK(Amount>0), CONSTRAINT CK_Payments_Method CHECK(Method IN(N'Cash',N'Card',N'Transfer'))
);
CREATE TABLE dbo.OrderStatusHistory (
 HistoryID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_OrderStatusHistory PRIMARY KEY, OrderID INT NOT NULL,
 OldStatus NVARCHAR(20) NULL, NewStatus NVARCHAR(20) NOT NULL, ChangedAt DATETIME2(0) NOT NULL CONSTRAINT DF_History_ChangedAt DEFAULT SYSUTCDATETIME(), Note NVARCHAR(250) NULL,
 CONSTRAINT FK_History_Orders FOREIGN KEY(OrderID) REFERENCES dbo.Orders(OrderID) ON DELETE NO ACTION ON UPDATE NO ACTION,
 CONSTRAINT CK_History_Old CHECK(OldStatus IS NULL OR OldStatus IN(N'New',N'Confirmed',N'InTransit',N'Delivered',N'Cancelled')),
 CONSTRAINT CK_History_New CHECK(NewStatus IN(N'New',N'Confirmed',N'InTransit',N'Delivered',N'Cancelled'))
);
CREATE INDEX IX_Vehicles_Type ON dbo.Vehicles(VehicleTypeID);
CREATE INDEX IX_Routes_ToCity ON dbo.Routes(ToCityID);
CREATE INDEX IX_Tariffs_Type ON dbo.Tariffs(VehicleTypeID);
CREATE INDEX IX_Orders_Client ON dbo.Orders(ClientID);
CREATE INDEX IX_Orders_Route ON dbo.Orders(RouteID);
CREATE INDEX IX_Orders_Tariff ON dbo.Orders(TariffID);
CREATE INDEX IX_Orders_StatusPickup ON dbo.Orders(Status,PickupDate) INCLUDE(QuotedAmount);
CREATE INDEX IX_CargoItems_Order ON dbo.CargoItems(OrderID) INCLUDE(WeightKg,VolumeM3,Quantity);
CREATE INDEX IX_CargoItems_Type ON dbo.CargoItems(CargoTypeID);
CREATE INDEX IX_Trips_VehicleTime ON dbo.Trips(VehicleID,DepartureAt,ArrivalAt) INCLUDE(Status,OrderID);
CREATE INDEX IX_Trips_DriverTime ON dbo.Trips(DriverID,DepartureAt,ArrivalAt) INCLUDE(Status,OrderID);
CREATE INDEX IX_Payments_Order ON dbo.Payments(OrderID) INCLUDE(Amount);
CREATE INDEX IX_History_OrderTime ON dbo.OrderStatusHistory(OrderID,ChangedAt,HistoryID);

EXEC(N'CREATE FUNCTION dbo.fn_OrderQuote(@OrderID INT)
RETURNS DECIMAL(14,2)
AS
BEGIN
 -- Bounded SUM preserves scale 4 through multiplication/addition; round only once.
 DECLARE @Amount DECIMAL(14,2);
 SELECT @Amount=CASE WHEN c.ItemCount=0 THEN 0 ELSE CONVERT(DECIMAL(14,2),ROUND(t.BasePrice+r.DistanceKm*t.PricePerKm+c.TotalWeight*t.PricePerKg,2)) END
 FROM dbo.Orders o JOIN dbo.Routes r ON r.RouteID=o.RouteID JOIN dbo.Tariffs t ON t.TariffID=o.TariffID
 CROSS APPLY(SELECT COUNT_BIG(*) ItemCount,CONVERT(DECIMAL(18,2),COALESCE(SUM(WeightKg),0)) TotalWeight FROM dbo.CargoItems WHERE OrderID=o.OrderID)c
 WHERE o.OrderID=@OrderID;
 RETURN COALESCE(@Amount,0);
END');
EXEC(N'CREATE TRIGGER dbo.trg_Orders_AuditAndValidate ON dbo.Orders AFTER INSERT,UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE i.OrderNumber<>d.OrderNumber) THROW 51025,N''Тапсырыс нөмірі өзгермейді.'',1;
 IF EXISTS(SELECT 1 FROM inserted i LEFT JOIN deleted d ON d.OrderID=i.OrderID WHERE d.OrderID IS NULL AND (i.Status<>N''New'' OR i.QuotedAmount<>0))
  THROW 51001,N''Жаңа тапсырыс New күйімен және 0 бағамен тіркелуі керек.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE i.Status<>d.Status AND NOT
   ((d.Status=N''New'' AND i.Status IN(N''Confirmed'',N''Cancelled'')) OR (d.Status=N''Confirmed'' AND i.Status IN(N''InTransit'',N''Cancelled'')) OR (d.Status=N''InTransit'' AND i.Status=N''Delivered'')))
  THROW 51002,N''Тапсырыс күйін бұлай ауыстыруға болмайды.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE
   (i.ClientID<>d.ClientID OR i.RouteID<>d.RouteID OR i.TariffID<>d.TariffID OR i.PickupDate<>d.PickupDate OR i.QuotedAmount<>d.QuotedAmount)
   AND (d.Status NOT IN(N''New'',N''Confirmed'') OR EXISTS(SELECT 1 FROM dbo.Payments p WITH(UPDLOCK,HOLDLOCK) WHERE p.OrderID=i.OrderID)
   OR EXISTS(SELECT 1 FROM dbo.Trips x WITH(UPDLOCK,HOLDLOCK) WHERE x.OrderID=i.OrderID AND x.Status<>N''Cancelled'')))
  THROW 51003,N''Төлемі не белсенді рейсі бар немесе аяқталған тапсырыстың негізгі деректері өзгермейді.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE i.QuotedAmount<>d.QuotedAmount AND i.QuotedAmount<>dbo.fn_OrderQuote(i.OrderID))
  THROW 51004,N''Баға тариф формуласына сәйкес болуы керек. Қайта есептеу рәсімін қолданыңыз.'',1;
 IF EXISTS(SELECT 1 FROM inserted i LEFT JOIN deleted d ON d.OrderID=i.OrderID JOIN dbo.Tariffs t ON t.TariffID=i.TariffID
   WHERE (d.OrderID IS NULL OR i.TariffID<>d.TariffID OR (i.Status=N''Confirmed'' AND d.Status=N''New'')) AND t.IsActive=0)
  THROW 51005,N''Жаңа тапсырысқа белсенді тариф таңдаңыз.'',1;
 IF EXISTS(SELECT 1 FROM inserted i WHERE i.Status IN(N''Confirmed'',N''InTransit'',N''Delivered'') AND (i.QuotedAmount<=0 OR NOT EXISTS(SELECT 1 FROM dbo.CargoItems c WHERE c.OrderID=i.OrderID)))
  THROW 51006,N''Тапсырысты растау үшін жүк пен оң баға қажет.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE i.Status=N''InTransit'' AND d.Status<>i.Status AND NOT EXISTS(SELECT 1 FROM dbo.Trips t WHERE t.OrderID=i.OrderID AND t.Status IN(N''Planned'',N''InTransit'')))
  THROW 51007,N''Жолға шығару үшін жоспарланған рейс қажет.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.OrderID=i.OrderID WHERE i.Status=N''Delivered'' AND d.Status<>i.Status AND NOT EXISTS(SELECT 1 FROM dbo.Trips t WHERE t.OrderID=i.OrderID AND t.Status IN(N''InTransit'',N''Completed'')))
  THROW 51008,N''Жеткізілді күйіне тек жолдағы рейсті өткізуге болады.'',1;
 IF EXISTS(SELECT 1 FROM inserted i WHERE i.Status=N''Cancelled'' AND EXISTS(SELECT 1 FROM dbo.Payments p WITH(UPDLOCK,HOLDLOCK) WHERE p.OrderID=i.OrderID))
  THROW 51009,N''Төлемі бар тапсырысты тоқтатуға болмайды.'',1;
 INSERT dbo.OrderStatusHistory(OrderID,OldStatus,NewStatus,Note)
 SELECT i.OrderID,d.Status,i.Status,CONVERT(NVARCHAR(250),SESSION_CONTEXT(N''QazCargo.StatusNote''))
 FROM inserted i LEFT JOIN deleted d ON d.OrderID=i.OrderID WHERE d.OrderID IS NULL OR i.Status<>d.Status;
 UPDATE t SET Status=CASE i.Status WHEN N''InTransit'' THEN N''InTransit'' WHEN N''Delivered'' THEN N''Completed'' ELSE N''Cancelled'' END
 FROM dbo.Trips t JOIN inserted i ON i.OrderID=t.OrderID JOIN deleted d ON d.OrderID=i.OrderID
 WHERE i.Status<>d.Status AND i.Status IN(N''InTransit'',N''Delivered'',N''Cancelled'');
 -- Route/tariff changes while editable always recalculate the saved quote.
 UPDATE o SET QuotedAmount=dbo.fn_OrderQuote(o.OrderID)
 FROM dbo.Orders o JOIN inserted i ON i.OrderID=o.OrderID JOIN deleted d ON d.OrderID=i.OrderID
 WHERE i.RouteID<>d.RouteID OR i.TariffID<>d.TariffID;
END');
EXEC(N'CREATE TRIGGER dbo.trg_CargoItems_ValidateAndPrice ON dbo.CargoItems AFTER INSERT,UPDATE,DELETE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.CargoItemID=i.CargoItemID WHERE i.OrderID<>d.OrderID) THROW 51026,N''Жүк басқа тапсырысқа көшірілмейді.'',1;
 DECLARE @Affected TABLE(OrderID INT PRIMARY KEY);
 INSERT @Affected SELECT OrderID FROM inserted UNION SELECT OrderID FROM deleted;
 IF EXISTS(SELECT 1 FROM dbo.Orders o WITH(UPDLOCK,HOLDLOCK) JOIN @Affected a ON a.OrderID=o.OrderID
  WHERE o.Status NOT IN(N''New'',N''Confirmed'') OR EXISTS(SELECT 1 FROM dbo.Payments p WHERE p.OrderID=o.OrderID)
  OR EXISTS(SELECT 1 FROM dbo.Trips t WHERE t.OrderID=o.OrderID AND t.Status<>N''Cancelled''))
  THROW 51010,N''Жүкті тек төлемі және белсенді рейсі жоқ New/Confirmed тапсырыста өзгертуге болады.'',1;
 IF EXISTS(SELECT 1 FROM dbo.Orders o JOIN @Affected a ON a.OrderID=o.OrderID WHERE o.Status=N''Confirmed'' AND NOT EXISTS(SELECT 1 FROM dbo.CargoItems c WHERE c.OrderID=o.OrderID))
  THROW 51011,N''Расталған тапсырыстың соңғы жүк позициясын өшіруге болмайды.'',1;
 UPDATE o SET QuotedAmount=dbo.fn_OrderQuote(o.OrderID) FROM dbo.Orders o JOIN @Affected a ON a.OrderID=o.OrderID;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Trips_Validate ON dbo.Trips AFTER INSERT,UPDATE,DELETE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 DECLARE @LockResult INT;
 EXEC @LockResult=sys.sp_getapplock @Resource=N''QazCargo.TripSchedule'',@LockMode=N''Exclusive'',@LockOwner=N''Transaction'',@LockTimeout=10000;
 IF @LockResult<0 THROW 51012,N''Рейстер кестесі бос емес. Әрекетті қайталаңыз.'',1;
 IF EXISTS(SELECT 1 FROM deleted d LEFT JOIN inserted i ON i.TripID=d.TripID WHERE i.TripID IS NULL AND d.Status IN(N''InTransit'',N''Completed''))
  THROW 51013,N''Жолдағы немесе аяқталған рейсті өшіруге болмайды.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.TripID=i.TripID WHERE i.OrderID<>d.OrderID)
  THROW 51014,N''Рейсті басқа тапсырысқа ауыстыруға болмайды.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.TripID=i.TripID WHERE d.Status IN(N''InTransit'',N''Completed'') AND
  (i.VehicleID<>d.VehicleID OR i.DriverID<>d.DriverID OR i.DepartureAt<>d.DepartureAt OR i.ArrivalAt<>d.ArrivalAt))
  THROW 51015,N''Жолдағы немесе аяқталған рейстің деректері өзгермейді.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN dbo.Orders o ON o.OrderID=i.OrderID WHERE
  NOT ((i.Status=N''Planned'' AND o.Status=N''Confirmed'') OR (i.Status=N''InTransit'' AND o.Status=N''InTransit'') OR (i.Status=N''Completed'' AND o.Status=N''Delivered'') OR (i.Status=N''Cancelled'' AND o.Status IN(N''Confirmed'',N''Cancelled''))))
  THROW 51016,N''Рейс күйі тапсырыс күйімен сәйкес емес. Күйлерді тапсырыс арқылы басқарыңыз.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN dbo.Orders o ON o.OrderID=i.OrderID JOIN dbo.Tariffs t ON t.TariffID=o.TariffID
  JOIN dbo.Vehicles v WITH(UPDLOCK,HOLDLOCK) ON v.VehicleID=i.VehicleID JOIN dbo.Drivers d WITH(UPDLOCK,HOLDLOCK) ON d.DriverID=i.DriverID
  WHERE i.Status<>N''Cancelled'' AND (v.VehicleTypeID<>t.VehicleTypeID OR v.CapacityKg<(SELECT SUM(c.WeightKg) FROM dbo.CargoItems c WHERE c.OrderID=i.OrderID)
   OR (i.Status IN(N''Planned'',N''InTransit'') AND (v.IsActive=0 OR d.IsActive=0))))
  THROW 51017,N''Көлік түрі, жүк көтерімділігі немесе көлік/жүргізуші белсенділігі сәйкес емес.'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN dbo.Orders o ON o.OrderID=i.OrderID WHERE i.Status<>N''Cancelled'' AND CONVERT(DATE,(i.DepartureAt AT TIME ZONE ''UTC'') AT TIME ZONE COALESCE(CONVERT(nvarchar(128),SESSION_CONTEXT(N''QazCargo.TimeZone'')),N''Qyzylorda Standard Time''))<o.PickupDate)
  THROW 51018,N''Рейстің шығуы жүкті алу күнінен ерте болмауы керек (Қазақстанның жергілікті күні).'',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN dbo.Trips t WITH(UPDLOCK,HOLDLOCK) ON t.TripID<>i.TripID
  AND (t.VehicleID=i.VehicleID OR t.DriverID=i.DriverID) AND i.DepartureAt<t.ArrivalAt AND t.DepartureAt<i.ArrivalAt
  WHERE i.Status<>N''Cancelled'' AND t.Status<>N''Cancelled'')
  THROW 51019,N''Осы уақытта көлік немесе жүргізуші басқа рейске тағайындалған.'',1;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Payments_Validate ON dbo.Payments AFTER INSERT,UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.PaymentID=i.PaymentID WHERE i.OrderID<>d.OrderID) THROW 51027,N''Төлем басқа тапсырысқа көшірілмейді.'',1;
 IF EXISTS(SELECT 1 FROM dbo.Orders o WITH(UPDLOCK,HOLDLOCK) WHERE o.OrderID IN(SELECT OrderID FROM inserted)
  AND (o.Status=N''Cancelled'' OR o.QuotedAmount<=0 OR (SELECT SUM(p.Amount) FROM dbo.Payments p WITH(UPDLOCK,HOLDLOCK) WHERE p.OrderID=o.OrderID)>o.QuotedAmount))
  THROW 51020,N''Төлем сомасы тапсырыс бағасынан аспауы керек; тоқтатылған не бағасы нөл тапсырысқа төлем жоқ.'',1;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Routes_ProtectUsed ON dbo.Routes AFTER UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.RouteID=i.RouteID WHERE (i.FromCityID<>d.FromCityID OR i.ToCityID<>d.ToCityID) AND EXISTS(SELECT 1 FROM dbo.Orders o WHERE o.RouteID=i.RouteID))
  THROW 51021,N''Қолданылған бағыттың қалалары өзгермейді. Қашықтықты түзету бұрынғы бағаны өзгертпейді.'',1;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Tariffs_ProtectUsed ON dbo.Tariffs AFTER UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.TariffID=i.TariffID WHERE
  (i.VehicleTypeID<>d.VehicleTypeID OR i.BasePrice<>d.BasePrice OR i.PricePerKm<>d.PricePerKm OR i.PricePerKg<>d.PricePerKg) AND EXISTS(SELECT 1 FROM dbo.Orders o WHERE o.TariffID=i.TariffID))
  THROW 51022,N''Қолданылған тарифтің есептеу параметрлері өзгермейді. Жаңа тариф нұсқасын қосыңыз.'',1;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Vehicles_ProtectScheduled ON dbo.Vehicles AFTER UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.VehicleID=i.VehicleID WHERE
  (i.VehicleTypeID<>d.VehicleTypeID OR i.CapacityKg<>d.CapacityKg OR i.IsActive<>d.IsActive) AND EXISTS(SELECT 1 FROM dbo.Trips t WITH(UPDLOCK,HOLDLOCK) WHERE t.VehicleID=i.VehicleID AND t.Status IN(N''Planned'',N''InTransit'')))
  THROW 51023,N''Жоспарланған не жолдағы рейсі бар көліктің түрі, жүк көтерімділігі және белсенділігі өзгермейді.'',1;
END');
EXEC(N'CREATE TRIGGER dbo.trg_Drivers_ProtectScheduled ON dbo.Drivers AFTER UPDATE
AS
BEGIN
 SET NOCOUNT ON;
 IF NOT EXISTS(SELECT 1 FROM inserted) AND NOT EXISTS(SELECT 1 FROM deleted) RETURN;
 IF EXISTS(SELECT 1 FROM inserted i JOIN deleted d ON d.DriverID=i.DriverID WHERE i.IsActive<>d.IsActive AND EXISTS(SELECT 1 FROM dbo.Trips t WITH(UPDLOCK,HOLDLOCK) WHERE t.DriverID=i.DriverID AND t.Status IN(N''Planned'',N''InTransit'')))
  THROW 51024,N''Жоспарланған не жолдағы рейсі бар жүргізушінің белсенділігі өзгермейді.'',1;
END');
EXEC(N'CREATE PROCEDURE dbo.usp_RepriceOrder @OrderID INT
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 BEGIN TRY
  BEGIN TRANSACTION;
  DECLARE @Status NVARCHAR(20),@TariffActive BIT;
  SELECT @Status=o.Status,@TariffActive=t.IsActive FROM dbo.Orders o WITH(UPDLOCK,HOLDLOCK) JOIN dbo.Tariffs t ON t.TariffID=o.TariffID WHERE o.OrderID=@OrderID;
  IF @Status IS NULL THROW 51030,N''Тапсырыс табылмады.'',1;
  IF @Status NOT IN(N''New'',N''Confirmed'') OR EXISTS(SELECT 1 FROM dbo.Payments WHERE OrderID=@OrderID) OR EXISTS(SELECT 1 FROM dbo.Trips WHERE OrderID=@OrderID AND Status<>N''Cancelled'')
   THROW 51031,N''Қайта есептеу үшін New/Confirmed күйі, төлемнің және белсенді рейстің болмауы қажет.'',1;
  IF @TariffActive=0 THROW 51032,N''Қайта есептеу үшін белсенді тариф қажет.'',1;
  UPDATE dbo.Orders SET QuotedAmount=dbo.fn_OrderQuote(@OrderID) WHERE OrderID=@OrderID;
  COMMIT TRANSACTION;
  SELECT QuotedAmount AS Amount FROM dbo.Orders WHERE OrderID=@OrderID;
 END TRY
 BEGIN CATCH
  IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
  THROW;
 END CATCH
END');
EXEC(N'CREATE PROCEDURE dbo.usp_SetOrderStatus @OrderID INT,@NewStatus NVARCHAR(20),@Note NVARCHAR(250)=NULL
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 BEGIN TRY
  BEGIN TRANSACTION;
  IF NOT EXISTS(SELECT 1 FROM dbo.Orders WITH(UPDLOCK,HOLDLOCK) WHERE OrderID=@OrderID) THROW 51030,N''Тапсырыс табылмады.'',1;
  EXEC sys.sp_set_session_context @key=N''QazCargo.StatusNote'',@value=@Note;
  UPDATE dbo.Orders SET Status=@NewStatus WHERE OrderID=@OrderID;
  EXEC sys.sp_set_session_context @key=N''QazCargo.StatusNote'',@value=NULL;
  COMMIT TRANSACTION;
 END TRY
 BEGIN CATCH
  IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
  EXEC sys.sp_set_session_context @key=N''QazCargo.StatusNote'',@value=NULL;
  THROW;
 END CATCH
END');
EXEC(N'CREATE VIEW dbo.v_OrderOverview
AS
 SELECT o.OrderID,o.OrderNumber,o.ClientID,o.RouteID,o.TariffID,o.Notes,c.Name AS ClientName,f.Name AS FromCity,t.Name AS ToCity,r.DistanceKm,
 o.OrderDate,o.PickupDate,o.Status,ta.Name AS TariffName,o.QuotedAmount,
 COALESCE(ci.TotalWeightKg,0) AS TotalWeightKg,COALESCE(ci.TotalVolumeM3,0) AS TotalVolumeM3,COALESCE(ci.Packages,0) AS Packages,
 COALESCE(p.PaidAmount,0) AS PaidAmount,o.QuotedAmount-COALESCE(p.PaidAmount,0) AS BalanceAmount,
 tr.TripID,tr.Status AS TripStatus,v.PlateNumber,d.FullName AS DriverName,tr.DepartureAt,tr.ArrivalAt
 FROM dbo.Orders o JOIN dbo.Clients c ON c.ClientID=o.ClientID JOIN dbo.Routes r ON r.RouteID=o.RouteID
 JOIN dbo.Cities f ON f.CityID=r.FromCityID JOIN dbo.Cities t ON t.CityID=r.ToCityID JOIN dbo.Tariffs ta ON ta.TariffID=o.TariffID
 OUTER APPLY(SELECT SUM(WeightKg) TotalWeightKg,SUM(VolumeM3) TotalVolumeM3,SUM(CONVERT(BIGINT,Quantity)) Packages FROM dbo.CargoItems WHERE OrderID=o.OrderID)ci
 OUTER APPLY(SELECT SUM(Amount) PaidAmount FROM dbo.Payments WHERE OrderID=o.OrderID)p
 LEFT JOIN dbo.Trips tr ON tr.OrderID=o.OrderID LEFT JOIN dbo.Vehicles v ON v.VehicleID=tr.VehicleID LEFT JOIN dbo.Drivers d ON d.DriverID=tr.DriverID;');


CREATE TABLE dbo.Users (
 UserID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Users PRIMARY KEY,
 Email NVARCHAR(120) NOT NULL CONSTRAINT UQ_Users_Email UNIQUE,
 FullName NVARCHAR(120) NOT NULL,
 PasswordHash NVARCHAR(255) NOT NULL,
 Role VARCHAR(10) NOT NULL CONSTRAINT CK_Users_Role CHECK(Role IN ('admin','client')),
 ClientID INT NULL CONSTRAINT FK_Users_Clients REFERENCES dbo.Clients(ClientID),
 IsActive BIT NOT NULL CONSTRAINT DF_Users_Active DEFAULT 1,
 AuthVersion INT NOT NULL CONSTRAINT DF_Users_Version DEFAULT 1,
 FailedAttempts INT NOT NULL CONSTRAINT DF_Users_Failed DEFAULT 0,
 LockedUntil DATETIME2(0) NULL,
 CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Users_Created DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_Users_Client CHECK ((Role='client' AND ClientID IS NOT NULL) OR (Role='admin' AND ClientID IS NULL))
);
CREATE UNIQUE INDEX UX_Users_Client ON dbo.Users(ClientID) WHERE ClientID IS NOT NULL;
CREATE TABLE dbo.Documents (
 DocumentID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Documents PRIMARY KEY,
 Title NVARCHAR(160) NOT NULL, OriginalName NVARCHAR(255) NOT NULL,
 MediaType VARCHAR(100) NOT NULL, Category VARCHAR(20) NOT NULL DEFAULT 'other',
 OrderID INT NULL CONSTRAINT FK_Documents_Orders REFERENCES dbo.Orders(OrderID),
 OwnerUserID INT NOT NULL CONSTRAINT FK_Documents_Users REFERENCES dbo.Users(UserID),
 FileSize INT NOT NULL, Content VARBINARY(MAX) NOT NULL,
 CreatedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_Documents_Size CHECK(FileSize BETWEEN 1 AND 20971520 AND DATALENGTH(Content)=FileSize),
 CONSTRAINT CK_Documents_Title CHECK(LEN(LTRIM(RTRIM(Title)))>0),
 CONSTRAINT CK_Documents_Category CHECK(Category IN ('contract','invoice','waybill','photo','report','other'))
);
CREATE INDEX IX_Documents_Order ON dbo.Documents(OrderID,CreatedAt);
CREATE INDEX IX_Documents_Owner ON dbo.Documents(OwnerUserID,CreatedAt);
CREATE TABLE dbo.SupportTickets (
 TicketID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SupportTickets PRIMARY KEY,
 UserID INT NOT NULL CONSTRAINT FK_SupportTickets_Users REFERENCES dbo.Users(UserID),
 OrderID INT NULL CONSTRAINT FK_SupportTickets_Orders REFERENCES dbo.Orders(OrderID),
 Subject NVARCHAR(160) NOT NULL,
 Status VARCHAR(20) NOT NULL DEFAULT 'Open' CONSTRAINT CK_SupportTickets_Status CHECK(Status IN ('Open','InProgress','Closed')),
 CreatedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
 UpdatedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_SupportTickets_User ON dbo.SupportTickets(UserID,UpdatedAt);
CREATE TABLE dbo.TicketMessages (
 MessageID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_TicketMessages PRIMARY KEY,
 TicketID INT NOT NULL CONSTRAINT FK_TicketMessages_Ticket REFERENCES dbo.SupportTickets(TicketID),
 UserID INT NOT NULL CONSTRAINT FK_TicketMessages_Users REFERENCES dbo.Users(UserID),
 Body NVARCHAR(2000) NOT NULL CONSTRAINT CK_TicketMessages_Body CHECK(LEN(LTRIM(RTRIM(Body)))>0),
 CreatedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_TicketMessages_Ticket ON dbo.TicketMessages(TicketID,MessageID);


CREATE INDEX IX_Orders_Date ON dbo.Orders(OrderDate) INCLUDE(ClientID,Status,QuotedAmount);
CREATE INDEX IX_Payments_Date ON dbo.Payments(PaidAt) INCLUDE(OrderID,Amount);
CREATE INDEX IX_SupportTickets_Order ON dbo.SupportTickets(OrderID);
CREATE INDEX IX_TicketMessages_User ON dbo.TicketMessages(UserID);
ALTER TABLE dbo.SupportTickets ADD CONSTRAINT CK_Support_Subject CHECK(LEN(LTRIM(RTRIM(Subject)))>0);
ALTER TABLE dbo.Users ADD CONSTRAINT CK_Users_NameEmail CHECK(LEN(LTRIM(RTRIM(FullName)))>0 AND LEN(LTRIM(RTRIM(Email)))>0);
EXEC(N'CREATE TRIGGER dbo.trg_History_Immutable ON dbo.OrderStatusHistory INSTEAD OF UPDATE,DELETE AS
BEGIN SET NOCOUNT ON; IF EXISTS(SELECT 1 FROM deleted) THROW 51028,N''Мәртебе тарихы өзгертілмейді.'',1; END');
EXEC(N'CREATE TRIGGER dbo.trg_TicketMessages_Validate ON dbo.TicketMessages AFTER INSERT AS
BEGIN
 SET NOCOUNT ON;
 IF EXISTS(SELECT 1 FROM inserted i JOIN dbo.SupportTickets t ON t.TicketID=i.TicketID JOIN dbo.Users u ON u.UserID=i.UserID
  WHERE t.Status=''Closed'' OR (u.Role<>''admin'' AND u.UserID<>t.UserID)) THROW 51029,N''Жабық немесе бөтен өтінішке хабарлама жіберілмейді.'',1;
END');
 COMMIT TRANSACTION;
 EXEC sys.sp_set_session_context @key=N'QazCargo.CreateAuthorized',@value=NULL;
 PRINT N'QazCargo: 17 tables, accounts, documents and support ready.';
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 EXEC sys.sp_set_session_context @key=N'QazCargo.CreateAuthorized',@value=NULL;
 THROW;
END CATCH;
GO
