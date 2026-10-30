USE QazCargo;
GO
-- 04 және 05 миграцияларынан кейін: 19 кесте, 25 FK.
SELECT COUNT(*) AS TableCount FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo');
SELECT name FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo') ORDER BY name;
SELECT name,type_desc FROM sys.objects WHERE type IN ('P','V','FN','TR') AND is_ms_shipped=0 ORDER BY type,name;
-- Құпиясөз хешін шығармайтын аккаунт тексерісі
SELECT UserID,Email,FullName,Role,ClientID,IsActive FROM dbo.Users;
-- Клиенттен жасалған нақты тапсырыс пен екі қаласы
SELECT TOP(20) * FROM dbo.v_OrderOverview ORDER BY OrderID DESC;
-- Жүк салмағы Quantity-ге қайта көбейтілмейді
SELECT o.OrderNumber,c.Name,r.DistanceKm,f.Name AS FromCity,t.Name AS ToCity,
       SUM(ci.WeightKg) AS WeightKg,SUM(ci.VolumeM3) AS VolumeM3,SUM(ci.Quantity) AS Packages
FROM dbo.Orders o JOIN dbo.Clients c ON c.ClientID=o.ClientID JOIN dbo.Routes r ON r.RouteID=o.RouteID
JOIN dbo.Cities f ON f.CityID=r.FromCityID JOIN dbo.Cities t ON t.CityID=r.ToCityID
JOIN dbo.CargoItems ci ON ci.OrderID=o.OrderID
GROUP BY o.OrderNumber,c.Name,r.DistanceKm,f.Name,t.Name;
SELECT o.OrderNumber,p.Amount,p.Method,p.PaidAt FROM dbo.Payments p JOIN dbo.Orders o ON o.OrderID=p.OrderID;
SELECT o.OrderNumber,t.Status,v.PlateNumber,d.FullName,t.DepartureAt,t.ArrivalAt
FROM dbo.Trips t JOIN dbo.Orders o ON o.OrderID=t.OrderID JOIN dbo.Vehicles v ON v.VehicleID=t.VehicleID JOIN dbo.Drivers d ON d.DriverID=t.DriverID;
SELECT DocumentID,Title,OriginalName,OwnerUserID,OrderID,FileSize,DATALENGTH(Content) AS StoredBytes FROM dbo.Documents;
SELECT o.OrderNumber,h.OldStatus,h.NewStatus,h.ChangedAt FROM dbo.OrderStatusHistory h JOIN dbo.Orders o ON o.OrderID=h.OrderID ORDER BY h.HistoryID;
SELECT t.TicketID,t.Subject,t.Status,u.FullName,m.Body,m.CreatedAt FROM dbo.SupportTickets t JOIN dbo.TicketMessages m ON m.TicketID=t.TicketID JOIN dbo.Users u ON u.UserID=m.UserID;

-- Черновиктің байланыстары мен күйі; жеке Payload дерегін шығармайды.
SELECT DraftID,UserID,Step,Revision,UpdatedAt,SubmittedOrderID FROM dbo.OrderDrafts;

-- Бүкіл Қазақстан жол желісі. Қалыпты нәтиже: 90 ресми қала, 8010 бағыт.
SELECT COUNT(*) AS LocatedCities FROM dbo.Cities WHERE Latitude IS NOT NULL;
SELECT COUNT(*) AS SourcedRoadRoutes FROM dbo.Routes WHERE DistanceSource IS NOT NULL;
SELECT Name,Region,Latitude,Longitude,GeoSourceID,GeoSourceURL FROM dbo.Cities ORDER BY Name;
SELECT TOP(25) a.Name AS FromCity,b.Name AS ToCity,r.DistanceKm,r.DistanceSource,r.DistanceUpdatedAt
FROM dbo.Routes r JOIN dbo.Cities a ON a.CityID=r.FromCityID JOIN dbo.Cities b ON b.CityID=r.ToCityID ORDER BY a.Name,b.Name;
