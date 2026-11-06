"""Labs 3–4: HTTP behavior and database invariants in disposable SQLite."""
import unittest
from copy import deepcopy
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select
from .database.db import make_engine
from .database.models import CargoItem, Order, Tariff
from .main import create_app
from .seed import counts, seed_demo
from .verify_db import verify


def payload():
    return {"client_id": 1, "route_id": 1, "tariff_id": 1, "pickup_date": "2026-11-20",
            "notes": "Тест тапсырысы", "items": [{"cargo_type_id": 1, "description": "Қапталған жүк",
                "weight_kg": "10.00", "volume_m3": "0.500", "quantity": 2}]}


class CRUDTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(":memory:")
        seed_demo(self.engine)
        self.client = TestClient(create_app(self.engine))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()

    def create(self, data=None):
        response = self.client.post("/api/orders", json=data or payload())
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_generated_fields_price_and_persistence(self):
        response = self.client.post("/api/orders", json=payload())
        self.assertEqual(response.status_code, 201, response.text)
        order = response.json()
        self.assertEqual(response.headers["Location"], f'/api/orders/{order["id"]}')
        self.assertTrue(order["number"].startswith("LAB-"))
        self.assertEqual(Decimal(order["quoted_amount"]), Decimal("165150.00"))
        self.assertEqual(order["status"], "New")
        self.assertTrue(order["created_at"])
        self.assertEqual(self.client.get(response.headers["Location"]).json(), order)
        with Session(self.engine) as session:
            row = session.get(Order, order["id"])
            self.assertEqual(len(row.items), 1)
            self.assertEqual(row.QuotedAmount, Decimal("165150.00"))

    def test_validation_rejects_invalid_cargo_and_date(self):
        variants = []
        for key, val in (("weight_kg", "-1"), ("weight_kg", "NaN"), ("weight_kg", "1.001"),
                         ("volume_m3", "0"), ("description", "   "), ("quantity", 0), ("quantity", True)):
            data = payload(); data["items"][0][key] = val; variants.append(data)
        for key, val in (("pickup_date", "wrong"), ("items", []), ("client_id", True)):
            data = payload(); data[key] = val; variants.append(data)
        for data in variants:
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/orders", json=data).status_code, 422)
        self.assertEqual(self.client.get("/api/summary").json()["tables"]["Orders"], 3)

    def test_system_fields_cannot_be_forged(self):
        for key, value in (("id", 7), ("number", "FAKE"), ("created_at", "2020-01-01"),
                           ("status", "Delivered"), ("quoted_amount", "-100")):
            with self.subTest(field=key):
                data = payload(); data[key] = value
                self.assertEqual(self.client.post("/api/orders", json=data).status_code, 422)
                self.assertEqual(self.client.patch("/api/orders/1", json={key: value}).status_code, 422)

    def test_unknown_references_do_not_create_partial_order(self):
        for key in ("client_id", "route_id", "tariff_id", "cargo_type_id"):
            data = payload()
            (data["items"][0] if key == "cargo_type_id" else data)[key] = 9999
            self.assertEqual(self.client.post("/api/orders", json=data).status_code, 422)
        with Session(self.engine) as session:
            self.assertEqual(counts(session)["Orders"], 3)
            self.assertEqual(counts(session)["CargoItems"], 5)

    def test_database_failure_rolls_back_parent_and_children(self):
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TRIGGER reject_test BEFORE INSERT ON CargoItems BEGIN SELECT RAISE(ABORT, 'test'); END"))
        self.assertEqual(self.client.post("/api/orders", json=payload()).status_code, 409)
        with Session(self.engine) as session:
            self.assertEqual(counts(session)["Orders"], 3)
            self.assertEqual(counts(session)["CargoItems"], 5)
        with self.engine.begin() as connection:
            connection.execute(text("DROP TRIGGER reject_test"))
        self.create()

    def test_patch_one_field_preserves_every_other_field(self):
        before = self.client.get("/api/orders/1").json()
        after = self.client.patch("/api/orders/1", json={"notes": "Жаңа ескерту"}).json()
        expected = deepcopy(before); expected["notes"] = "Жаңа ескерту"
        self.assertEqual(after, expected)
        self.assertEqual(self.client.get("/api/orders/1").json(), expected)

    def test_patch_null_unset_and_empty_body(self):
        for data in ({}, {"client_id": None}, {"route_id": None}, {"tariff_id": None},
                     {"pickup_date": None}, {"items": None}, {"items": []}):
            with self.subTest(data=data):
                self.assertEqual(self.client.patch("/api/orders/1", json=data).status_code, 422)
        response = self.client.patch("/api/orders/1", json={"notes": None})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["notes"])

    def test_replace_items_recalculates_price(self):
        order = self.create()
        replacement = payload()["items"]
        replacement[0].update(weight_kg="20.00", cargo_type_id=2)
        response = self.client.patch(f'/api/orders/{order["id"]}', json={"items": replacement})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["quoted_amount"], "165300.00")
        self.assertEqual(response.json()["cargo_types"], ["Азық-түлік"])
        with Session(self.engine) as session:
            self.assertEqual(len(session.get(Order, order["id"]).items), 1)
            self.assertEqual(counts(session)["CargoItems"], 6)

    def test_invalid_patch_is_atomic(self):
        before = self.client.get("/api/orders/1").json()
        bad = payload()["items"]; bad[0]["cargo_type_id"] = 9999
        response = self.client.patch("/api/orders/1", json={"notes": "must not persist", "items": bad})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/orders/1").json(), before)

    def test_delete_removes_only_this_order_and_its_items(self):
        order = self.create(); path = f'/api/orders/{order["id"]}'
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.patch(path, json={"notes": "x"}).status_code, 404)
        self.assertEqual(self.client.delete(path).status_code, 404)
        with Session(self.engine) as session:
            self.assertIsNone(session.get(Order, order["id"]))
            self.assertEqual(len(session.exec(select(CargoItem).where(CargoItem.OrderID == order["id"])).all()), 0)
            self.assertEqual(counts(session)["CargoItems"], 5)
            self.assertEqual(counts(session)["Clients"], 3)

    def test_missing_id_is_404(self):
        self.assertEqual(self.client.get("/api/orders/9999").status_code, 404)
        self.assertEqual(self.client.patch("/api/orders/9999", json={"notes": "x"}).status_code, 404)
        self.assertEqual(self.client.delete("/api/orders/9999").status_code, 404)

    def test_filters_and_pagination(self):
        order = self.create()
        result = self.client.get("/api/orders", params={"min_price": "165150", "max_price": "165150", "client_id": 1, "status": "New"}).json()
        self.assertEqual([o["id"] for o in result], [order["id"]])
        self.assertEqual(len(self.client.get("/api/orders", params={"search": "LAB-2026-00"}).json()), 3)
        self.assertEqual(len(self.client.get("/api/orders", params={"search": "Оқу клиенті 1"}).json()), 2)
        self.assertEqual(len(self.client.get("/api/orders", params={"max_price": "0"}).json()), 3)
        page = self.client.get("/api/orders", params={"limit": 1, "offset": 1}).json()
        self.assertEqual([o["id"] for o in page], [2])

    def test_search_uses_literal_bound_values(self):
        for value in ("%", "_", "' OR 1=1 --"):
            self.assertEqual(self.client.get("/api/orders", params={"search": value}).json(), [])

    def test_invalid_query_is_422(self):
        for params in ({"min_price": -1}, {"min_price": 2, "max_price": 1}, {"min_price": "NaN"},
                       {"limit": 0}, {"limit": 201}, {"offset": -1}, {"status": "Unknown"}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/api/orders", params=params).status_code, 422)

    def test_non_new_orders_are_protected(self):
        with Session(self.engine) as session:
            row = session.get(Order, 1); row.Status = "Confirmed"; session.add(row); session.commit()
        self.assertEqual(self.client.patch("/api/orders/1", json={"notes": "x"}).status_code, 409)
        self.assertEqual(self.client.delete("/api/orders/1").status_code, 409)

    def test_inactive_tariff_rejected(self):
        with Session(self.engine) as session:
            tariff = session.get(Tariff, 1); tariff.IsActive = False; session.add(tariff); session.commit()
        self.assertEqual(self.client.post("/api/orders", json=payload()).status_code, 409)

    def test_swagger_and_openapi_contract(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        spec = self.client.get("/openapi.json").json()
        self.assertIn("201", spec["paths"]["/api/orders"]["post"]["responses"])
        self.assertEqual(set(spec["paths"]["/api/orders/{order_id}"]), {"get", "patch", "delete"})
        self.assertNotIn("content", spec["paths"]["/api/orders/{order_id}"]["delete"]["responses"]["204"])
        props = spec["components"]["schemas"]["OrderCreate"]["properties"]
        self.assertNotIn("id", props)
        self.assertNotIn("quoted_amount", props)

    def test_seed_and_verify_after_legitimate_crud(self):
        for ident in (1, 2, 3):
            self.assertEqual(self.client.delete(f"/api/orders/{ident}").status_code, 204)
        self.assertFalse(seed_demo(self.engine)["inserted"])
        self.assertEqual(verify(self.engine)["tables"]["Orders"], 0)
        self.create()
        self.assertFalse(seed_demo(self.engine)["inserted"])
        self.assertEqual(verify(self.engine)["tables"]["Orders"], 1)


if __name__ == "__main__":
    unittest.main()
