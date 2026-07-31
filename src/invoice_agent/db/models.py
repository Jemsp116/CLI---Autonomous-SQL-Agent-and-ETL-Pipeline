from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    date_of_issue: Mapped[str | None] = mapped_column(String)
    seller_name: Mapped[str | None] = mapped_column(String)
    seller_address: Mapped[str | None] = mapped_column(String)
    seller_tax_id: Mapped[str | None] = mapped_column(String)
    seller_gstin: Mapped[str | None] = mapped_column(String)
    client_name: Mapped[str | None] = mapped_column(String)
    client_address: Mapped[str | None] = mapped_column(String)
    client_tax_id: Mapped[str | None] = mapped_column(String)

    line_items: Mapped[list[LineItem]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (
        UniqueConstraint("invoice_id", "item_no", name="uq_line_items_invoice_id_item_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_no: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String)
    qty: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    net_price: Mapped[float | None] = mapped_column(Float)
    net_worth: Mapped[float | None] = mapped_column(Float)
    vat_pct: Mapped[str | None] = mapped_column(String)
    gross_worth: Mapped[float | None] = mapped_column(Float)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")
