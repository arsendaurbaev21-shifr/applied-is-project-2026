from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlmodel import Session, select
from ..database.db import get_session
from ..database.models import Client, Order
from ..seed import counts
from ..schemas import OrderCreate, OrderRead, OrderStatus, OrderUpdate
from .. import services

router = APIRouter(prefix="/api", tags=["QazCargo оқу модулі"])


def order_view(order):
    return {
        "id": order.OrderID, "number": order.OrderNumber, "client": order.client.Name,
        "route": f"{order.route.origin.Name} → {order.route.destination.Name}",
        "client_id": order.ClientID, "route_id": order.RouteID, "tariff_id": order.TariffID,
        "status": order.Status, "pickup_date": order.PickupDate, "created_at": order.OrderDate,
        "notes": order.Notes, "quoted_amount": order.QuotedAmount,
        "cargo_types": [t.Name for t in order.cargo_types],
        "items": [{"id": i.CargoItemID, "cargo_type_id": i.CargoTypeID, "description": i.Description,
                   "type": i.cargo_type.Name, "weight_kg": str(i.WeightKg),
                   "volume_m3": str(i.VolumeM3), "quantity": i.Quantity} for i in order.items],
    }


@router.get("/summary")
def summary(session: Session = Depends(get_session)):
    return {"project": "QazCargo", "mode": "synthetic-lab-data", "tables": counts(session)}


@router.get("/clients")
def clients(session: Session = Depends(get_session)):
    return [{"id": c.ClientID, "name": c.Name, "order_count": len(c.orders)}
            for c in session.exec(select(Client).order_by(Client.ClientID)).all()]


@router.get("/orders", response_model=list[OrderRead], summary="Тапсырыстарды оқу және сүзгілеу")
def orders(session: Session = Depends(get_session), search: str | None = Query(default=None, max_length=120),
           min_price: Decimal | None = Query(default=None, ge=0, le=Decimal("999999999999.99")),
           max_price: Decimal | None = Query(default=None, ge=0, le=Decimal("999999999999.99")),
           client_id: int | None = Query(default=None, gt=0), status: OrderStatus | None = None,
           offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=200)):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "min_price max_price мәнінен үлкен болмауы тиіс")
    query = select(Order).join(Client)
    if search and search.strip():
        term = search.strip()
        query = query.where(or_(Order.OrderNumber.contains(term, autoescape=True), Client.Name.contains(term, autoescape=True)))
    if min_price is not None:
        query = query.where(Order.QuotedAmount >= min_price)
    if max_price is not None:
        query = query.where(Order.QuotedAmount <= max_price)
    if client_id is not None:
        query = query.where(Order.ClientID == client_id)
    if status is not None:
        query = query.where(Order.Status == status)
    query = query.order_by(Order.OrderID).offset(offset).limit(limit)
    return [order_view(o) for o in session.exec(query).all()]


@router.get("/orders/{order_id}", response_model=OrderRead, summary="Тапсырысты ID арқылы оқу")
def order_detail(order_id: int, session: Session = Depends(get_session)):
    return order_view(services.find_order(session, order_id))


@router.post("/orders", response_model=OrderRead, status_code=201, summary="Жаңа тапсырыс жасау")
def create_order(data: OrderCreate, response: Response, session: Session = Depends(get_session)):
    order = services.create_order(session, data)
    response.headers["Location"] = f"/api/orders/{order.OrderID}"
    return order_view(order)
