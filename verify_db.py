"""Деректер қорын тексереді, өзгертпейді."""

from sqlalchemy import func, inspect, text
from sqlmodel import Session, select

from app.database.db import DATABASE_PATH, engine
from app.database.models import Category, Item, ItemSupplier, Supplier


def main():
    if not DATABASE_PATH.exists():
        raise SystemExit("Database missing. Run python seed.py first.")
    engine.echo = False
    print("TABLES:", ", ".join(sorted(inspect(engine).get_table_names())))
    with Session(engine) as session:
        for model in [Category, Supplier, Item, ItemSupplier]:
            count = session.exec(select(func.count()).select_from(model)).one()
            print(f"{model.__tablename__}: {count}")
        print("FOREIGN_KEYS:", session.exec(text("PRAGMA foreign_keys")).scalar())
        print("FOREIGN_KEY_ERRORS:", session.exec(text("PRAGMA foreign_key_check")).all())
        print("INTEGRITY:", session.exec(text("PRAGMA integrity_check")).scalar())
        print("\nSKU | Item | Category | Suppliers | Stock | Price KZT")
        for item in session.exec(select(Item).order_by(Item.sku)).all():
            names = ", ".join(sorted(s.name for s in item.suppliers))
            print(f"{item.sku} | {item.name} | {item.category.name} | "
                  f"{names} | {item.stock_qty} | {item.price_tiyn / 100:.2f}")


if __name__ == "__main__":
    main()
