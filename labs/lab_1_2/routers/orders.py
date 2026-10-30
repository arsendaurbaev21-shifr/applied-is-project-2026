from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..database.db import get_session
from ..database.models import Client, Order
from ..seed import counts

router = APIRouter(prefix="/api", tags=["QazCargo оқу модулі"])


def order_view(order):
    return {
        "id": order.OrderID, "number": order.OrderNumber, "client": order.client.Name,
        "route": f"{order.route.origin.Name} → {order.route.destination.Name}",
        "status": order.Status, "pickup_date": order.PickupDate.isoformat(),
        "cargo_types": [t.Name for t in order.cargo_types],
        "items": [{"type": i.cargo_type.Name, "weight_kg": str(i.WeightKg),
                   "volume_m3": str(i.VolumeM3), "quantity": i.Quantity} for i in order.items],
    }


@router.get("/summary")
def summary(session: Session = Depends(get_session)):
    return {"project": "QazCargo", "mode": "synthetic-lab-data", "tables": counts(session)}


@router.get("/clients")
def clients(session: Session = Depends(get_session)):
    return [{"id": c.ClientID, "name": c.Name, "order_count": len(c.orders)}
            for c in session.exec(select(Client).order_by(Client.ClientID)).all()]


@router.get("/orders")
def orders(session: Session = Depends(get_session)):
    return [order_view(o) for o in session.exec(select(Order).order_by(Order.OrderID)).all()]


@router.get("/orders/{order_id}")
def order_detail(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Тапсырыс табылмады")
    return order_view(order)
