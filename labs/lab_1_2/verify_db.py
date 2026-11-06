import json
from sqlalchemy import inspect, text
from sqlmodel import Session, select
from .database.db import engine
from .database.models import CargoType, Client, Order
from .seed import counts


def verify(target=engine):
    with Session(target) as session:
        result = counts(session)
        assert session.exec(text("PRAGMA foreign_keys")).scalar() == 1
        assert session.exec(text("PRAGMA integrity_check")).scalar() == "ok"
        assert not session.exec(text("PRAGMA foreign_key_check")).all()
        for order in session.exec(select(Order)).all():
            assert order.items, f"Order {order.OrderID} has no cargo"
            assert {t.CargoTypeID for t in order.cargo_types} == {i.CargoTypeID for i in order.items}
        for cargo in session.exec(select(CargoType)).all():
            assert {o.OrderID for o in cargo.orders} == {i.OrderID for i in cargo.items}
        assert sum(len(c.orders) for c in session.exec(select(Client)).all()) == result["Orders"]
    foreign_keys = sum(len(inspect(target).get_foreign_keys(t)) for t in inspect(target).get_table_names())
    return {"tables": result, "foreign_keys": foreign_keys, "integrity": "ok", "one_to_many": "ok", "many_to_many": "ok"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
