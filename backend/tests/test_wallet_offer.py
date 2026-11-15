"""The home page's wallet cards read the price list without signing in:
the packages on sale, cheapest first, and the pass price."""

import os
import sys
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app


def pack(credits: int, price: int, active: bool = True) -> dict[str, object]:
    return {"id": str(uuid4()), "credits": credits, "price": price, "is_active": active, "sort_order": 0}


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    fake = MiniSupabase(
        {
            "club_settings": [{"id": 1, "pass_price": 299}],
            "credit_packages": [pack(5000, 4700), pack(500, 500), pack(1000, 950), pack(2000, 1900, active=False)],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


def test_offer_lists_packages_on_sale_cheapest_first_and_the_pass_price(db: MiniSupabase) -> None:
    res = TestClient(app).get("/api/wallet-offer")
    assert res.status_code == 200
    body = res.json()
    assert [(p["credits"], p["price"]) for p in body["packages"]] == [(500, 500), (1000, 950), (5000, 4700)]
    assert body["pass_price"] == 299


def test_offer_without_settings_falls_back_to_the_default_pass_price(db: MiniSupabase) -> None:
    db.tables["club_settings"] = []
    db.tables["credit_packages"] = []
    body = TestClient(app).get("/api/wallet-offer").json()
    assert body == {"packages": [], "pass_price": 249}
