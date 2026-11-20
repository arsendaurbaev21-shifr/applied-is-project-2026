import json
from sqlalchemy import inspect, text
from sqlmodel import Session, select
from .database.db import engine
from .database.models import CargoType, Client, Order
from .seed import counts


def require_valid(condition, message):
    if not condition:
        raise ValueError(message)


def verify(target=engine):
    with Session(target) as session:
        result = counts(session)
        require_valid(session.exec(text("PRAGMA foreign_keys")).scalar() == 1, "Foreign key enforcement is disabled")
        require_valid(session.exec(text("PRAGMA integrity_check")).scalar() == "ok", "SQLite integrity check failed")
        require_valid(not session.exec(text("PRAGMA foreign_key_check")).all(), "Foreign key violations found")
        for order in session.exec(select(Order)).all():
            require_valid(bool(order.items), f"Order {order.OrderID} has no cargo")
            require_valid({t.CargoTypeID for t in order.cargo_types} == {i.CargoTypeID for i in order.items}, "Order relationship mismatch")
        for cargo in session.exec(select(CargoType)).all():
            require_valid({o.OrderID for o in cargo.orders} == {i.OrderID for i in cargo.items}, "Cargo relationship mismatch")
        require_valid(sum(len(c.orders) for c in session.exec(select(Client)).all()) == result["Orders"], "Client relationship mismatch")
    foreign_keys = sum(len(inspect(target).get_foreign_keys(t)) for t in inspect(target).get_table_names())
    return {"tables": result, "foreign_keys": foreign_keys, "integrity": "ok", "one_to_many": "ok", "many_to_many": "ok"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
