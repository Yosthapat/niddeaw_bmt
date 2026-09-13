from app.services import expense_service


def _expense(
    expense_date: str, category: str, amount: float, is_paid: bool = False
) -> expense_service.ExpenseRow:
    return {
        "expense_date": expense_date,
        "category": category,
        "amount": amount,
        "is_paid": is_paid,
    }


def test_groups_by_month_and_sums_total() -> None:
    expenses = [
        _expense("2026-09-05", "court_fee", 800.0),
        _expense("2026-09-12", "shuttlecock", 290.0),
        _expense("2026-08-30", "jersey", 1500.0),
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert [s.month for s in result] == ["2026-09", "2026-08"]
    september = result[0]
    assert september.total_amount == 1090.0
    assert september.expense_count == 2


def test_sums_by_category_within_a_month() -> None:
    expenses = [
        _expense("2026-09-01", "court_fee", 800.0),
        _expense("2026-09-02", "court_fee", 800.0),
        _expense("2026-09-03", "other", 150.0),
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert result[0].by_category == {"court_fee": 1600.0, "other": 150.0}


def test_empty_input_returns_empty_list() -> None:
    assert expense_service.build_monthly_summary([]) == []


def test_paid_amount_counts_only_reimbursed_expenses() -> None:
    # An expense an admin fronted but hasn't been paid back for is a debt the
    # club owes, not money that has left its account — the account-balance
    # donut on the dashboard reads paid_amount for exactly that reason.
    expenses = [
        _expense("2026-09-01", "court_fee", 800.0, is_paid=True),
        _expense("2026-09-02", "shuttlecock", 290.0, is_paid=False),
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert result[0].total_amount == 1090.0
    assert result[0].paid_amount == 800.0


def test_paid_amount_is_zero_when_nothing_reimbursed() -> None:
    result = expense_service.build_monthly_summary([_expense("2026-09-01", "other", 500.0)])

    assert result[0].total_amount == 500.0
    assert result[0].paid_amount == 0.0


def test_paid_amount_tracks_total_when_everything_reimbursed() -> None:
    expenses = [
        _expense("2026-09-01", "court_fee", 800.0, is_paid=True),
        _expense("2026-09-02", "jersey", 1500.0, is_paid=True),
    ]
    result = expense_service.build_monthly_summary(expenses)

    assert result[0].paid_amount == result[0].total_amount == 2300.0
