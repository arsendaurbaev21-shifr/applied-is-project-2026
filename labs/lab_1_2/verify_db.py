import json
from sqlalchemy import inspect, text
from sqlmodel import Session, select
from .database.db import engine
from .database.models import CargoType, Client, Order
from .seed import counts, EXPECTED


def verify(target=engine):
    with Session(target) as session:
        result = counts(session)
        assert result == EXPECTED, result
        assert session.exec(text("PRAGMA foreign_keys")).scalar() == 1
        assert session.exec(text("PRAGMA integrity_check")).scalar() == "ok"
        assert not session.exec(text("PRAGMA foreign_key_check")).all()
        order = session.exec(select(Order).where(Order.OrderNumber == "LAB-2026-001")).one()
        assert len(order.items) == 2 and len(order.cargo_types) == 2
        cargo = session.exec(select(CargoType).where(CargoType.Name == "Жалпы жүк")).one()
        assert len(cargo.orders) == 2
        assert sum(len(c.orders) for c in session.exec(select(Client)).all()) == 3
    foreign_keys = sum(len(inspect(target).get_foreign_keys(t)) for t in inspect(target).get_table_names())
    return {"tables": result, "foreign_keys": foreign_keys, "integrity": "ok", "one_to_many": "ok", "many_to_many": "ok"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
