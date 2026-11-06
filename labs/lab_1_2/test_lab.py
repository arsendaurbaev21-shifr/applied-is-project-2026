"""Isolated tests: SQLite only, no imports of the Flask/SQL Server backend."""
import unittest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from .database.db import get_session, make_engine
from .database.models import CargoItem, Client, Order
from .main import app
from .seed import seed_demo, counts, EXPECTED
from .verify_db import verify


class LabTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(":memory:")
        seed_demo(self.engine)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_seed_and_relationships(self):
        self.assertEqual(verify(self.engine)["foreign_keys"], 8)

    def test_repeated_seed_preserves_data(self):
        with Session(self.engine) as session:
            client = session.get(Client, 1)
            client.Name = "Өзгертілген оқу клиенті"
            session.add(client)
            session.commit()
        self.assertFalse(seed_demo(self.engine)["inserted"])
        with Session(self.engine) as session:
            self.assertEqual(counts(session), EXPECTED)
            self.assertEqual(session.get(Client, 1).Name, "Өзгертілген оқу клиенті")

    def test_orphan_foreign_key_rejected(self):
        with Session(self.engine) as session:
            session.add(CargoItem(OrderID=99999, CargoTypeID=1, Description="Test",
                                  WeightKg=Decimal("1"), VolumeM3=Decimal("1"), Quantity=1))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()
            self.assertEqual(counts(session), EXPECTED)

    def test_negative_weight_rejected(self):
        with Session(self.engine) as session:
            with self.assertRaises(IntegrityError):
                session.exec(text('UPDATE "CargoItems" SET "WeightKg"=-1 WHERE "CargoItemID"=1'))
                session.commit()
            session.rollback()

    def test_linked_client_delete_rejected(self):
        with Session(self.engine) as session:
            with self.assertRaises(IntegrityError):
                session.exec(text('DELETE FROM "Clients" WHERE "ClientID"=1'))
                session.commit()
            session.rollback()

    def test_decimal_round_trip(self):
        with Session(self.engine) as session:
            item = session.get(CargoItem, 1)
            self.assertEqual(item.WeightKg, Decimal("100.25"))
            self.assertEqual(item.VolumeM3, Decimal("1.125"))

    def test_duplicate_order_rejected(self):
        with Session(self.engine) as session:
            with self.assertRaises(IntegrityError):
                session.exec(text('UPDATE "Orders" SET "OrderNumber"=\'LAB-2026-001\' WHERE "OrderID"=2'))
                session.commit()
            session.rollback()

    def test_api_matches_orm_and_validates_empty_create(self):
        def session_override():
            with Session(self.engine) as session:
                yield session
        app.dependency_overrides[get_session] = session_override
        # No context manager: this test uses the seeded in-memory engine only.
        client = TestClient(app)
        try:
            self.assertEqual(client.get("/api/summary").json()["tables"], EXPECTED)
            orders = client.get("/api/orders").json()
            self.assertEqual(len(orders), 3)
            self.assertEqual(orders[0]["route"], "Алматы → Астана")
            self.assertEqual(len(orders[0]["cargo_types"]), 2)
            self.assertEqual(client.get("/api/orders/1").status_code, 200)
            self.assertEqual(client.get("/api/orders/9999").status_code, 404)
            self.assertEqual(client.post("/api/orders", json={}).status_code, 422)
            self.assertEqual(len(client.get("/api/clients").json()), 3)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
