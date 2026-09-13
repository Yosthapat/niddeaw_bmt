from datetime import date

from pydantic import BaseModel


class Season(BaseModel):
    """One calendar year of club play. See app/services/season_service.py
    for why seasons are derived from session dates instead of stored."""

    number: int
    year: int
    start_date: date
    end_date: date
    is_current: bool
