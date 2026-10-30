import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database.db import make_engine
from app.database.models import Category, Item, ItemSupplier, Supplier
from seed import seed_database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        path = (Path(self.directory.name) / "test.db").as_posix()
        self.engine = make_engine(f"sqlite:///{path}")
        seed_database(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()

    def test_tables_and_seed_counts(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()),
                         {"category", "supplier", "item", "item_supplier"})
        with Session(self.engine) as session:
            for model, expected in [(Category, 3), (Supplier, 3),
                                    (Item, 4), (ItemSupplier, 5)]:
                self.assertEqual(session.exec(
                    select(func.count()).select_from(model)).one(), expected)

    def test_seed_is_repeatable_and_preserves_edits(self):
        with Session(self.engine) as session:
            item = session.exec(select(Item).where(Item.sku == "EL-001")).one()
            item.stock_qty = 99
            session.add(item)
            session.commit()
        seed_database(self.engine)
        self.test_tables_and_seed_counts()
        with Session(self.engine) as session:
            item = session.exec(select(Item).where(Item.sku == "EL-001")).one()
            self.assertEqual(item.stock_qty, 99)

    def test_relationships_both_directions(self):
        with Session(self.engine) as session:
            item = session.exec(select(Item).where(Item.sku == "EL-001")).one()
            self.assertEqual(item.category.name, "Электроника")
            self.assertIn(item, item.category.items)
            self.assertEqual(len(item.suppliers), 2)
            for supplier in item.suppliers:
                self.assertIn(item, supplier.items)

    def assert_rejected(self, item):
        with Session(self.engine) as session:
            session.add(item)
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

    def test_invalid_foreign_key_rejected(self):
        self.assert_rejected(Item(sku="BAD-FK", name="Test", price_tiyn=100,
                                  stock_qty=1, category_id=999999))

    def test_negative_values_rejected_by_database(self):
        for price, quantity in [(-1, 0), (100, -1)]:
            with self.subTest(price=price, quantity=quantity):
                self.assert_rejected(Item(sku="BAD-NUM", name="Test",
                                          price_tiyn=price, stock_qty=quantity,
                                          category_id=1))

    def test_duplicate_sku_and_link_rejected(self):
        self.assert_rejected(Item(sku="EL-001", name="Test", price_tiyn=100,
                                  stock_qty=1, category_id=1))
        with Session(self.engine) as session:
            link = session.exec(select(ItemSupplier)).first()
            duplicate = ItemSupplier(item_id=link.item_id,
                                     supplier_id=link.supplier_id)
            session.expunge(link)
            session.add(duplicate)
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()


if __name__ == "__main__":
    unittest.main()
