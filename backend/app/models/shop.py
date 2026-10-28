from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.fields import Name, PositiveBaht

SaleType = Literal["stock", "preorder"]
OrderStatus = Literal["pending", "confirmed", "delivered", "rejected"]

Size = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
StockQty = Annotated[int, Field(ge=0, le=10000)]

ONE_SIZE = ""
"""The size key of a product that has none — a sticker set, a keychain."""

MAX_IMAGES = 4
MAX_SIZES = 12


class ProductFields(BaseModel):
    """What the admin form sends, on create and (all optional) on edit."""

    name: Name | None = None
    description: Description | None = None
    price: PositiveBaht | None = None
    sale_type: SaleType | None = None
    sizes: list[Size] | None = Field(default=None, max_length=MAX_SIZES)
    preorder_closes_on: date | None = None
    preorder_delivers_on: date | None = None
    # Stock per size ("" for one size). Only meaningful for sale_type
    # 'stock'; the router checks it matches the sizes.
    stock: dict[str, StockQty] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _distinct_sizes(self) -> Self:
        if self.sizes is not None and len({s.upper() for s in self.sizes}) != len(self.sizes):
            raise ValueError("a size is listed twice")
        return self


class ProductCreate(ProductFields):
    name: Name
    price: PositiveBaht
    sale_type: SaleType


class Product(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    price: float
    sale_type: SaleType
    sizes: list[str]
    preorder_closes_on: date | None = None
    preorder_delivers_on: date | None = None
    image_urls: list[str]
    is_active: bool
    sort_order: int
    created_at: datetime
    stock: dict[str, int] = {}
    """Per size, for sale_type 'stock'; empty for a pre-order."""
    ordered: int = 0
    """Units ordered and not rejected — what "สั่งแล้ว 21 ตัว" counts."""
    open: bool = True
    """Can be ordered right now: active, and either in stock or a
    pre-order that hasn't closed."""


class OrderPublic(BaseModel):
    """What a member sees of an order: no slip, no other member's data."""

    id: UUID
    order_no: int
    product_name: str
    sale_type: SaleType
    size: str
    qty: int
    total: float
    status: OrderStatus
    note: str | None = None
    created_at: datetime


class OrderAdmin(OrderPublic):
    player_id: UUID
    player_nickname: str
    player_code: str
    product_id: UUID | None = None
    unit_price: float
    slip_url: str
    updated_at: datetime


class OrderUpdate(BaseModel):
    status: OrderStatus
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


class PreorderTally(BaseModel):
    product_id: UUID
    name: str
    preorder_closes_on: date | None
    by_size: dict[str, int]
    total: int
