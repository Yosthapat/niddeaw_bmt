"""The expense categories live in three places — the database's check, the
API's model and the page's dropdown — and must be the same list in all
three. One left behind is a dropdown option the database refuses, or a
category the page cannot show."""

import re
from pathlib import Path
from typing import get_args

from app.models.expense import ExpenseCategory

ROOT = Path(__file__).resolve().parents[2]


def _quoted(text: str) -> set[str]:
    return set(re.findall(r"'([a-z_]+)'", text))


def database_categories() -> set[str]:
    # The newest migration that sets the check is the one in force.
    latest: set[str] = set()
    for path in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        for found in re.finditer(r"check \(category in \(([^)]*)\)\)", path.read_text()):
            latest = _quoted(found.group(1))
    return latest


def page_categories() -> set[str]:
    view = (ROOT / "frontend" / "src" / "views" / "admin" / "ExpensesView.vue").read_text()
    found = re.search(r"const CATEGORIES: ExpenseCategory\[\] = \[([^\]]*)\]", view)
    assert found
    return _quoted(found.group(1))


def test_the_three_lists_agree() -> None:
    api = set(get_args(ExpenseCategory))
    assert database_categories() == api
    assert page_categories() == api


def test_dividend_is_one_of_them() -> None:
    assert "dividend" in get_args(ExpenseCategory)


def test_every_category_has_a_thai_and_an_english_name() -> None:
    for locale in ("th", "en"):
        text = (ROOT / "frontend" / "src" / "i18n" / "locales" / f"{locale}.ts").read_text()
        block = re.search(r"categoryLabels: \{([^}]*)\}", text)
        assert block, locale
        named = set(re.findall(r"(\w+):", block.group(1)))
        assert named == set(get_args(ExpenseCategory)), locale
