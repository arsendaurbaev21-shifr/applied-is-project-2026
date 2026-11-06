"""Labs 3–4: public request/response schemas, separate from database tables."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveID = Annotated[int, Field(gt=0, strict=True)]
Weight = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Volume = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
OrderStatus = Literal["New", "Confirmed", "InTransit", "Delivered", "Cancelled"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CargoItemCreate(InputModel):
    cargo_type_id: PositiveID
    description: str = Field(min_length=1, max_length=200)
    weight_kg: Weight = Field(description="Позицияның жалпы салмағы, кг; Quantity-ге көбейтілмейді")
    volume_m3: Volume
    quantity: int = Field(gt=0, le=2147483647, strict=True)


class OrderCreate(InputModel):
    client_id: PositiveID
    route_id: PositiveID
    tariff_id: PositiveID
    pickup_date: date
    notes: str | None = Field(default=None, max_length=500)
    items: list[CargoItemCreate] = Field(min_length=1, max_length=100)
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "client_id": 1, "route_id": 1, "tariff_id": 1, "pickup_date": "2026-11-20",
        "notes": "Зертханалық тапсырыс",
        "items": [{"cargo_type_id": 1, "description": "Қапталған жүк",
                   "weight_kg": "10.00", "volume_m3": "0.500", "quantity": 2}]
    }]})


class OrderUpdate(InputModel):
    client_id: PositiveID | None = None
    route_id: PositiveID | None = None
    tariff_id: PositiveID | None = None
    pickup_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[CargoItemCreate] | None = Field(default=None, min_length=1, max_length=100)
    model_config = ConfigDict(json_schema_extra={"examples": [{"notes": "Алушыға алдын ала хабарласу"}]})

    @model_validator(mode="after")
    def reject_invalid_nulls(self):
        if not self.model_fields_set:
            raise ValueError("Кемінде бір өзгертілетін өріс жіберіңіз")
        for field in self.model_fields_set - {"notes"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} үшін null рұқсат етілмейді")
        return self


class CargoItemRead(BaseModel):
    id: int
    cargo_type_id: int
    type: str
    description: str
    weight_kg: Decimal
    volume_m3: Decimal
    quantity: int


class OrderRead(BaseModel):
    id: int
    number: str
    client_id: int
    client: str
    route_id: int
    route: str
    tariff_id: int
    status: OrderStatus
    pickup_date: date
    created_at: datetime
    notes: str | None
    quoted_amount: Decimal
    cargo_types: list[str]
    items: list[CargoItemRead]
