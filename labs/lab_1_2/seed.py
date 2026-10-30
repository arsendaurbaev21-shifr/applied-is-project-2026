"""Insert 3–5 synthetic rows into each lab table, atomically and without deletion."""
import json
from datetime import date
from decimal import Decimal as D
from sqlalchemy import func
from sqlmodel import Session, select
from .database.db import init_db, make_engine
from .database.models import CargoItem, CargoType, City, Client, Order, Route, Tariff, VehicleType

MODELS = (City, Route, VehicleType, Tariff, Client, Order, CargoType, CargoItem)
EXPECTED = {m.__tablename__: 5 if m is CargoItem else 3 for m in MODELS}


def counts(session):
    return {m.__tablename__: session.exec(select(func.count()).select_from(m)).one() for m in MODELS}


def seed_demo(engine):
    init_db(engine)
    with Session(engine) as session:
        existing = counts(session)
        if any(existing.values()):
            if all(existing[name] >= n for name, n in EXPECTED.items()):
                return {"inserted": False, "counts": existing}
            raise RuntimeError("Оқу базасы жартылай толтырылған. Seed деректерді өзгертпеді.")
        cities = [City(Name=name) for name in ("Алматы", "Астана", "Шымкент")]
        types = [VehicleType(Name=name) for name in ("Тент", "Рефрижератор", "Шағын фургон")]
        clients = [Client(Name=f"Оқу клиенті {i}", Phone="DEMO", Email=f"client{i}@example.invalid") for i in range(1, 4)]
        cargo = [CargoType(Name=name, Description="QazCargo оқу дерегі") for name in ("Жалпы жүк", "Азық-түлік", "Жабдық")]
        session.add_all(cities + types + clients + cargo)
        session.flush()
        # Approximate demonstration distances, not the production OSRM snapshot.
        routes = [Route(origin=cities[a], destination=cities[b], DistanceKm=D(km))
                  for a, b, km in ((0, 1, "1250"), (0, 2, "690"), (1, 2, "1500"))]
        tariffs = [Tariff(Name=f"Оқу тарифі {i+1}", vehicle_type=v, BasePrice=D(base), PricePerKm=D(km), PricePerKg=D(kg))
                   for i, (v, base, km, kg) in enumerate(zip(types, ("15000", "25000", "8000"), ("120", "160", "80"), ("15", "20", "10")))]
        session.add_all(routes + tariffs)
        session.flush()
        orders = [Order(OrderNumber=f"LAB-2026-{i+1:03d}", client=clients[i], route=routes[i], tariff=tariffs[i],
                        PickupDate=date(2026, 11, 10+i), Notes="Тек зертханаға арналған мысал") for i in range(3)]
        session.add_all(orders)
        session.flush()
        positions = ((0, 0, "100.25", "1.125", 4), (0, 2, "50", "0.500", 1),
                     (1, 1, "220", "2.000", 10), (2, 0, "80", "0.900", 3), (2, 2, "150", "1.500", 2))
        for oi, ci, kg, volume, quantity in positions:
            session.add(CargoItem(order=orders[oi], cargo_type=cargo[ci], Description=f"Оқу жүк позициясы {oi+1}-{ci+1}",
                                  WeightKg=D(kg), VolumeM3=D(volume), Quantity=quantity))
        session.commit()
        return {"inserted": True, "counts": counts(session)}


if __name__ == "__main__":
    engine = make_engine(echo=True)
    try:
        print(json.dumps(seed_demo(engine), ensure_ascii=False, indent=2))
    finally:
        engine.dispose()
