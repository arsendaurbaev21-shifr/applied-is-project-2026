"""Тестілік деректер: 3 категория, 3 жеткізуші, 4 тауар, 5 байланыс."""

from sqlmodel import Session, select

from app.database.db import engine, init_db
from app.database.models import Category, Item, Supplier


def seed_database(db_engine=engine):
    init_db(db_engine)
    with Session(db_engine) as session:
        categories = {}
        for name, description in [
            ("Электроника", "Компьютер және кеңсе техникасы"),
            ("Кеңсе тауарлары", "Күнделікті кеңсе керек-жарақтары"),
            ("Шаруашылық тауарлары", "Үй-жайға арналған тауарлар"),
        ]:
            row = session.exec(select(Category).where(Category.name == name)).first()
            if row is None:
                row = Category(name=name, description=description)
                session.add(row)
                session.flush()
            categories[name] = row

        suppliers = {}
        for name, phone in [
            ("Demo Tech Supply", "+7 (000) 000-00-01"),
            ("Demo Office Market", "+7 (000) 000-00-02"),
            ("Demo Universal Trade", "+7 (000) 000-00-03"),
        ]:
            row = session.exec(select(Supplier).where(Supplier.name == name)).first()
            if row is None:
                row = Supplier(name=name, phone=phone)
                session.add(row)
                session.flush()
            suppliers[name] = row

        data = [
            ("EL-001", "Пернетақта", 1450000, 12, "Электроника",
             ["Demo Tech Supply", "Demo Universal Trade"]),
            ("OF-001", "A4 қағазы", 250000, 25, "Кеңсе тауарлары",
             ["Demo Office Market"]),
            ("OF-002", "Дәптер", 45000, 40, "Кеңсе тауарлары",
             ["Demo Office Market"]),
            ("HH-001", "Үстел шамы", 890000, 8, "Шаруашылық тауарлары",
             ["Demo Universal Trade"]),
        ]
        for sku, name, price, quantity, category, supplier_names in data:
            row = session.exec(select(Item).where(Item.sku == sku)).first()
            if row is None:
                row = Item(
                    sku=sku, name=name, price_tiyn=price, stock_qty=quantity,
                    category_id=categories[category].id,
                )
                session.add(row)
            existing_ids = {supplier.id for supplier in row.suppliers}
            for supplier_name in supplier_names:
                supplier = suppliers[supplier_name]
                if supplier.id not in existing_ids:
                    row.suppliers.append(supplier)
                    existing_ids.add(supplier.id)
        session.commit()


if __name__ == "__main__":
    seed_database()
    print("Seed completed. Run python verify_db.py to inspect the database.")
