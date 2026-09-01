from app.services import expense_service


def test_groups_by_month_and_sums_total() -> None:
    expenses = [
        {"expense_date": "2026-09-05", "category": "court_fee", "amount": 800.0},
        {"expense_date": "2026-09-12", "category": "shuttlecock", "amount": 290.0},
        {"expense_date": "2026-08-30", "category": "jersey", "amount": 1500.0},
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert [s.month for s in result] == ["2026-09", "2026-08"]
    september = result[0]
    assert september.total_amount == 1090.0
    assert september.expense_count == 2


def test_sums_by_category_within_a_month() -> None:
    expenses = [
        {"expense_date": "2026-09-01", "category": "court_fee", "amount": 800.0},
        {"expense_date": "2026-09-02", "category": "court_fee", "amount": 800.0},
        {"expense_date": "2026-09-03", "category": "other", "amount": 150.0},
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert result[0].by_category == {"court_fee": 1600.0, "other": 150.0}


def test_empty_input_returns_empty_list() -> None:
    assert expense_service.build_monthly_summary([]) == []
