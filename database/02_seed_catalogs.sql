/* ОҚУ МЫСАЛЫ. Қашықтық, тариф, көлік пен жүргізуші коммерциялық дерек емес.
   Клиенттер, аккаунттар, тапсырыстар мен төлемдер бұл файлда жасалмайды. */
USE QazCargo;
GO
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 IF EXISTS(SELECT 1 FROM dbo.Cities) THROW 51000,N'Анықтамалықтар бос емес. Seed қайта орындалмайды.',1;
 INSERT dbo.Cities(Name) VALUES(N'Астана'),(N'Шымкент'),(N'Алматы'),(N'Қызылорда'),(N'Қарағанды'),(N'Ақтөбе');
 INSERT dbo.VehicleTypes(Name) VALUES(N'Тент'),(N'Рефрижератор'),(N'Шағын фургон');
 INSERT dbo.CargoTypes(Name,Description) VALUES(N'Жалпы жүк',N'Қапталған құрғақ жүк'),(N'Азық-түлік',N'Температура талаптарын ескеріңіз'),(N'Жабдық',N'Орау мен бекіту қажет'),(N'Жиһаз',N'Қорғаныш қаптамамен');
 INSERT dbo.Routes(FromCityID,ToCityID,DistanceKm) VALUES(1,2,1500),(2,1,1500),(1,3,1250),(3,2,690),(4,2,450),(1,5,220),(6,4,1200);
 INSERT dbo.Tariffs(Name,VehicleTypeID,BasePrice,PricePerKm,PricePerKg) VALUES
 (N'Стандарт · оқу үлгісі',1,15000,120,15),(N'Салқын жүк · оқу үлгісі',2,25000,160,20),(N'Шағын жүк · оқу үлгісі',3,8000,80,10);
 INSERT dbo.Vehicles(VehicleTypeID,PlateNumber,Brand,CapacityKg) VALUES(1,N'DEMO-001',N'Volvo · оқу үлгісі',20000),(2,N'DEMO-002',N'MAN · оқу үлгісі',15000),(3,N'DEMO-003',N'Ford · оқу үлгісі',1500),(1,N'DEMO-004',N'DAF · оқу үлгісі',18000);
 INSERT dbo.Drivers(FullName,Phone,LicenseNumber) VALUES(N'Оқу жүргізушісі 1',N'Оқу үлгісі',N'DEMO-LIC-001'),(N'Оқу жүргізушісі 2',N'Оқу үлгісі',N'DEMO-LIC-002'),(N'Оқу жүргізушісі 3',N'Оқу үлгісі',N'DEMO-LIC-003');
 COMMIT;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK;
 THROW;
END CATCH;
GO
