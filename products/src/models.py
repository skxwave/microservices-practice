from decimal import Decimal

from sqlalchemy import CheckConstraint, String, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(256))
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        CheckConstraint("price >= 0", name="check_price_positive"),
        nullable=False,
    )

    @validates("price")
    def validate_price(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Price cannot be negative")
        return value
