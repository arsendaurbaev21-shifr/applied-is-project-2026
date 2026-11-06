"""Atomic order writes for the isolated lab database; no SQL Server imports."""
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from .database.models import CargoItem, CargoType, Client, Order, Route, Tariff
from .schemas import OrderCreate, OrderUpdate


def find_order(session: Session, order_id: int):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Тапсырыс табылмады")
    return order


def references(session, client_id, route_id, tariff_id, items=None):
    for model, ident, name in ((Client, client_id, "client_id"), (Route, route_id, "route_id"), (Tariff, tariff_id, "tariff_id")):
        if session.get(model, ident) is None:
            raise HTTPException(422, f"{name}: анықтамалықта мұндай жазба жоқ")
    tariff = session.get(Tariff, tariff_id)
    if not tariff.IsActive:
        raise HTTPException(409, "Таңдалған тариф белсенді емес")
    for item in items or []:
        if session.get(CargoType, item.cargo_type_id) is None:
            raise HTTPException(422, "cargo_type_id: жүк түрі табылмады")
    return session.get(Route, route_id), tariff


def calculate_quote(route, tariff, weights):
    # Matches the original QazCargo formula: WeightKg already includes all units.
    total = tariff.BasePrice + route.DistanceKm * tariff.PricePerKm + sum(weights, Decimal(0)) * tariff.PricePerKg
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if total > Decimal("999999999999.99"):
        raise HTTPException(422, "Есептелген баға рұқсат етілген шектен асады")
    return total


def item_row(order_id, data):
    return CargoItem(OrderID=order_id, CargoTypeID=data.cargo_type_id, Description=data.description,
                     WeightKg=data.weight_kg, VolumeM3=data.volume_m3, Quantity=data.quantity)


def editable(order):
    if order.Status != "New":
        raise HTTPException(409, "Тек New күйіндегі оқу тапсырысын өзгертуге немесе өшіруге болады")


def create_order(session: Session, data: OrderCreate):
    route, tariff = references(session, data.client_id, data.route_id, data.tariff_id, data.items)
    quote = calculate_quote(route, tariff, (i.weight_kg for i in data.items))
    order = Order(OrderNumber="LAB-" + uuid4().hex[:20].upper(), ClientID=data.client_id,
                  RouteID=data.route_id, TariffID=data.tariff_id, PickupDate=data.pickup_date,
                  Notes=data.notes, QuotedAmount=quote)
    try:
        session.add(order)
        session.flush()
        session.add_all([item_row(order.OrderID, item) for item in data.items])
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Жазба дерекқор шектеулеріне сәйкес келмейді") from None
    session.refresh(order)
    return order


def update_order(session: Session, order_id: int, data: OrderUpdate):
    order = find_order(session, order_id)
    editable(order)
    changes = data.model_dump(exclude_unset=True)
    route, tariff = references(session, changes.get("client_id", order.ClientID),
                              changes.get("route_id", order.RouteID), changes.get("tariff_id", order.TariffID), data.items)
    mapping = {"client_id": "ClientID", "route_id": "RouteID", "tariff_id": "TariffID",
               "pickup_date": "PickupDate", "notes": "Notes"}
    updates = {mapping[k]: v for k, v in changes.items() if k in mapping}
    if {"route_id", "tariff_id", "items"} & changes.keys():
        weights = (i.weight_kg for i in data.items) if "items" in changes else (i.WeightKg for i in order.items)
        updates["QuotedAmount"] = calculate_quote(route, tariff, weights)
    try:
        order.sqlmodel_update(updates)
        session.add(order)
        if "items" in changes:
            session.exec(delete(CargoItem).where(CargoItem.OrderID == order_id))
            session.add_all([item_row(order_id, item) for item in data.items])
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Өзгеріс дерекқор шектеулеріне сәйкес келмейді") from None
    session.refresh(order)
    return order


def delete_order(session: Session, order_id: int):
    order = find_order(session, order_id)
    editable(order)
    try:
        # Remove this order's dependent rows explicitly in the same transaction.
        session.exec(delete(CargoItem).where(CargoItem.OrderID == order_id))
        session.delete(order)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Тапсырыс басқа жазбамен байланысқан") from None
