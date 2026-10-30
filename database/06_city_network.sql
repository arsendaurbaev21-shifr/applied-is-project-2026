-- Additive migration. IDs and existing orders are retained.
SET XACT_ABORT ON;
IF COL_LENGTH('dbo.Cities','Latitude') IS NULL
 ALTER TABLE dbo.Cities ADD Latitude decimal(9,6) NULL, Longitude decimal(9,6) NULL,
 Region nvarchar(100) NULL, GeoSourceID nvarchar(80) NULL, GeoSourceURL nvarchar(350) NULL;
GO
IF COL_LENGTH('dbo.Routes','DistanceSource') IS NULL
 ALTER TABLE dbo.Routes ADD DistanceSource nvarchar(100) NULL, DistanceUpdatedAt date NULL;
GO
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name='CK_Cities_Coordinates')
 ALTER TABLE dbo.Cities ADD CONSTRAINT CK_Cities_Coordinates CHECK
 ((Latitude IS NULL AND Longitude IS NULL) OR (Latitude BETWEEN -90 AND 90 AND Longitude BETWEEN -180 AND 180 AND Latitude IS NOT NULL AND Longitude IS NOT NULL));
GO
