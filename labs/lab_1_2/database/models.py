"""QazCargo table/column names, adapted to an isolated SQLite teaching database.

Four principal entities: Client, Order, CargoType, CargoItem (association).
City/Route/VehicleType/Tariff retain the existing order references.
This is a subset of the SQL Server schema, not its migration or replacement.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from pydantic import NaiveDatetime
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class CargoItem(SQLModel, table=True):
    __tablename__ = "CargoItems"
    __table_args__ = (
        CheckConstraint('"WeightKg" > 0'), CheckConstraint('"VolumeM3" > 0'),
        CheckConstraint('"Quantity" > 0'),
    )
    CargoItemID: int | None = Field(default=None, primary_key=True)
    OrderID: int = Field(foreign_key="Orders.OrderID", index=True)
    CargoTypeID: int = Field(foreign_key="CargoTypes.CargoTypeID", index=True)
    Description: str = Field(max_length=200)
    WeightKg: Decimal = Field(max_digits=12, decimal_places=2)
    VolumeM3: Decimal = Field(max_digits=12, decimal_places=3)
    Quantity: int = Field(gt=0)
    order: "Order" = Relationship(back_populates="items")
    cargo_type: "CargoType" = Relationship(back_populates="items")


class Client(SQLModel, table=True):
    __tablename__ = "Clients"
    ClientID: int | None = Field(default=None, primary_key=True)
    Name: str = Field(max_length=120)
    Phone: str = Field(max_length=30)
    Email: str | None = Field(default=None, max_length=120)
    Address: str | None = Field(default=None, max_length=250)
    CreatedAt: NaiveDatetime = Field(default_factory=utc_now)
    orders: list["Order"] = Relationship(back_populates="client")


class CargoType(SQLModel, table=True):
    __tablename__ = "CargoTypes"
    CargoTypeID: int | None = Field(default=None, primary_key=True)
    Name: str = Field(max_length=80, unique=True)
    Description: str | None = Field(default=None, max_length=250)
    items: list[CargoItem] = Relationship(back_populates="cargo_type")
    orders: list["Order"] = Relationship(
        back_populates="cargo_types", link_model=CargoItem,
        sa_relationship_kwargs={"viewonly": True},
    )


class City(SQLModel, table=True):
    __tablename__ = "Cities"
    CityID: int | None = Field(default=None, primary_key=True)
    Name: str = Field(max_length=80, unique=True)
    outgoing: list["Route"] = Relationship(
        back_populates="origin", sa_relationship_kwargs={"foreign_keys": "Route.FromCityID"})
    incoming: list["Route"] = Relationship(
        back_populates="destination", sa_relationship_kwargs={"foreign_keys": "Route.ToCityID"})


class Route(SQLModel, table=True):
    __tablename__ = "Routes"
    __table_args__ = (
        UniqueConstraint("FromCityID", "ToCityID"),
        CheckConstraint('"FromCityID" != "ToCityID"'), CheckConstraint('"DistanceKm" > 0'),
    )
    RouteID: int | None = Field(default=None, primary_key=True)
    FromCityID: int = Field(foreign_key="Cities.CityID")
    ToCityID: int = Field(foreign_key="Cities.CityID")
    DistanceKm: Decimal = Field(max_digits=10, decimal_places=2)
    origin: City = Relationship(
        back_populates="outgoing", sa_relationship_kwargs={"foreign_keys": "Route.FromCityID"})
    destination: City = Relationship(
        back_populates="incoming", sa_relationship_kwargs={"foreign_keys": "Route.ToCityID"})
    orders: list["Order"] = Relationship(back_populates="route")


class VehicleType(SQLModel, table=True):
    __tablename__ = "VehicleTypes"
    VehicleTypeID: int | None = Field(default=None, primary_key=True)
    Name: str = Field(max_length=60, unique=True)
    tariffs: list["Tariff"] = Relationship(back_populates="vehicle_type")


class Tariff(SQLModel, table=True):
    __tablename__ = "Tariffs"
    __table_args__ = (CheckConstraint('"BasePrice" >= 0 AND "PricePerKm" >= 0 AND "PricePerKg" >= 0'),)
    TariffID: int | None = Field(default=None, primary_key=True)
    Name: str = Field(max_length=100)
    VehicleTypeID: int = Field(foreign_key="VehicleTypes.VehicleTypeID")
    BasePrice: Decimal = Field(max_digits=14, decimal_places=2)
    PricePerKm: Decimal = Field(max_digits=12, decimal_places=2)
    PricePerKg: Decimal = Field(max_digits=12, decimal_places=2)
    IsActive: bool = True
    vehicle_type: VehicleType = Relationship(back_populates="tariffs")
    orders: list["Order"] = Relationship(back_populates="tariff")


class Order(SQLModel, table=True):
    __tablename__ = "Orders"
    __table_args__ = (
        CheckConstraint('"Status" IN (\'New\',\'Confirmed\',\'InTransit\',\'Delivered\',\'Cancelled\')'),
        CheckConstraint('"QuotedAmount" >= 0'),
    )
    OrderID: int | None = Field(default=None, primary_key=True)
    OrderNumber: str = Field(max_length=30, unique=True)
    ClientID: int = Field(foreign_key="Clients.ClientID", index=True)
    RouteID: int = Field(foreign_key="Routes.RouteID")
    TariffID: int = Field(foreign_key="Tariffs.TariffID")
    OrderDate: NaiveDatetime = Field(default_factory=utc_now)
    PickupDate: date
    Status: str = Field(default="New", max_length=20)
    Notes: str | None = Field(default=None, max_length=500)
    QuotedAmount: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    client: Client = Relationship(back_populates="orders")
    route: Route = Relationship(back_populates="orders")
    tariff: Tariff = Relationship(back_populates="orders")
    items: list[CargoItem] = Relationship(back_populates="order")
    cargo_types: list[CargoType] = Relationship(
        back_populates="orders", link_model=CargoItem,
        sa_relationship_kwargs={"viewonly": True},
    )
