"""ЛР 2: үш негізгі мән және көптен көпке байланыс кестесі."""

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


class ItemSupplier(SQLModel, table=True):
    __tablename__ = "item_supplier"

    item_id: int = Field(foreign_key="item.id", primary_key=True)
    supplier_id: int = Field(foreign_key="supplier.id", primary_key=True)


class Category(SQLModel, table=True):
    __tablename__ = "category"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    description: str = Field(default="", max_length=255)
    items: list["Item"] = Relationship(back_populates="category")


class Supplier(SQLModel, table=True):
    __tablename__ = "supplier"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    phone: str = Field(max_length=30)
    items: list["Item"] = Relationship(
        back_populates="suppliers", link_model=ItemSupplier
    )


class Item(SQLModel, table=True):
    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint("price_tiyn >= 0", name="ck_item_price_nonnegative"),
        CheckConstraint("stock_qty >= 0", name="ck_item_stock_nonnegative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True, max_length=40)
    name: str = Field(index=True, max_length=150)
    price_tiyn: int = Field(ge=0)
    stock_qty: int = Field(default=0, ge=0)
    category_id: int = Field(foreign_key="category.id", index=True)

    category: Category = Relationship(back_populates="items")
    suppliers: list[Supplier] = Relationship(
        back_populates="items", link_model=ItemSupplier
    )
