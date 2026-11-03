from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.fields import EditForm, Name, PositiveBaht

SaleType = Literal["stock", "preorder"]
OrderStatus = Literal["pending", "confirmed", "delivered", "rejected"]

Size = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
StockQty = Annotated[int, Field(ge=0, le=10000)]

ONE_SIZE = ""
"""The size key of a product that has none — a sticker set, a keychain."""

MAX_IMAGES = 4
MAX_SIZES = 16
MAX_CART_LINES = 20
MAX_LINE_QTY = 10


class ProductFields(EditForm):
    """What the admin form sends, on create and (all optional) on edit."""

    NOT_NULL = frozenset({"name", "price", "sale_type", "sizes", "size_prices", "is_active"})

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
    # Price per size where it isn't `price` (XL +20). The router checks the
    # keys are sizes the product has.
    size_prices: dict[str, PositiveBaht] | None = None
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
    size_prices: dict[str, float] = {}
    """Per size where it isn't `price`; see unit_price()."""
    stock: dict[str, int] = {}
    """Per size, for sale_type 'stock'; empty for a pre-order."""
    ordered: int = 0
    """Units ordered and not rejected — what "สั่งแล้ว 21 ตัว" counts."""
    open: bool = True
    """Can be ordered right now: active, and either in stock or a
    pre-order that hasn't closed."""


class OrderItem(BaseModel):
    id: UUID | None = None
    product_id: UUID | None = None
    product_name: str
    sale_type: SaleType
    size: str
    qty: int
    unit_price: float
    line_total: float


class OrderPublic(BaseModel):
    """What a member sees of an order: no slip, no other member's data."""

    id: UUID
    order_no: int
    items: list[OrderItem]
    total: float
    status: OrderStatus
    note: str | None = None
    created_at: datetime


class OrderAdmin(OrderPublic):
    player_id: UUID | None = None
    """None for a guest's order."""
    player_nickname: str
    """The member's nickname, or the name a guest typed."""
    player_code: str
    guest: bool = False
    guest_phone: str | None = None
    """Only ever sent to the admin: never in a public response."""
    slip_url: str
    updated_at: datetime


GuestName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


def phone_digits(raw: str) -> str | None:
    """A Thai phone number as its digits (0812345678), or None when it
    isn't one: a leading 0 and 9 or 10 digits, whatever dashes or spaces
    were typed between them."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) in (9, 10) and digits.startswith("0"):
        return digits
    return None


class OrderDelete(BaseModel):
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class CartLine(BaseModel):
    product_id: UUID
    size: Annotated[str, StringConstraints(strip_whitespace=True, max_length=12)] = ONE_SIZE
    qty: Annotated[int, Field(ge=1, le=MAX_LINE_QTY)]


class Cart(BaseModel):
    items: list[CartLine] = Field(min_length=1, max_length=MAX_CART_LINES)


class QuoteLine(BaseModel):
    product_id: UUID
    product_name: str
    image_url: str | None = None
    sale_type: SaleType
    size: str
    qty: int
    unit_price: float
    line_total: float
    problem: str | None = None
    """Why this line can't be bought as it is (sold out, closed, gone) —
    the cart shows it beside the line. None when it's fine."""
    available: int | None = None
    """For a stock line: how many of that size are left."""


class Quote(BaseModel):
    lines: list[QuoteLine]
    total: float
    ok: bool
    """Every line can be bought as it is."""


class OrderItemUpdate(BaseModel):
    """The admin fixing a line a member got wrong: the size, or how many."""

    size: Annotated[str, StringConstraints(strip_whitespace=True, max_length=12)] | None = None
    qty: Annotated[int, Field(ge=1, le=MAX_LINE_QTY)] | None = None


class OrderUpdate(BaseModel):
    status: OrderStatus
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


class PreorderTally(BaseModel):
    product_id: UUID
    name: str
    preorder_closes_on: date | None
    by_size: dict[str, int]
    total: int


class ShopRevenueDay(BaseModel):
    date: date
    amount: float
    orders: int


class ShopTopItem(BaseModel):
    name: str
    qty: int
    amount: float


class ShopRevenue(BaseModel):
    """Money in is confirmed + delivered orders; pending ones are apart and
    in no total. cost is the shop-cost and shirt expenses."""

    total: float
    orders: int
    pending_amount: float
    pending_orders: int
    to_ship: int
    cost: float
    profit: float
    daily: list[ShopRevenueDay]
    top: list[ShopTopItem]


def unit_price(product: dict[str, object], size: str) -> float:
    """What one of `size` costs: its own price if it has one, else the
    product's."""
    prices = product.get("size_prices") or {}
    own = prices.get(size) if isinstance(prices, dict) else None
    return round(float(str(own if own is not None else product["price"])), 2)
