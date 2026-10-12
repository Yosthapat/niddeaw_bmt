"""The three rules a nickname has to keep, judged on names the club uses."""

from __future__ import annotations

import pytest

from app.services.nickname_service import (
    EMPTY,
    MAX_LENGTH,
    NOT_CAPITALISED,
    NOT_ENGLISH,
    TOO_LONG,
    normalise,
    validation_error,
)

# Real names from the club's roster. If a rule ever rejects one of these,
# the rule is wrong, not the name.
REAL_NAMES = [
    "Zeer",
    "Aeya",
    "P'Tee",  # an apostrophe
    "AP",  # every letter capital
    "Pukpick",
    "Sompong",
    "Balll",
    "Ohmy",
]


@pytest.mark.parametrize("name", REAL_NAMES)
def test_every_name_the_club_already_uses_is_allowed(name: str) -> None:
    assert validation_error(name) is None


@pytest.mark.parametrize("name", ["Mary-Jane", "Big Boy", "O'Brien", "A"])
def test_the_shapes_the_rules_mean_to_allow(name: str) -> None:
    assert validation_error(name) is None


@pytest.mark.parametrize("name", ["บอล", "Ball บอล", "ボール", "Ball😀"])
def test_anything_but_english_is_refused(name: str) -> None:
    assert validation_error(name) == NOT_ENGLISH


@pytest.mark.parametrize("name", ["ball", "p'Tee", "mary-Jane", "big Boy"])
def test_a_lowercase_first_letter_is_refused(name: str) -> None:
    assert validation_error(name) == NOT_CAPITALISED


def test_a_name_that_is_english_but_oddly_punctuated_hears_about_the_letters() -> None:
    """"Ball2" is not a capitalisation problem, so it must not be reported
    as one — that would send the admin looking for the wrong thing."""
    assert validation_error("Ball2") == NOT_ENGLISH
    assert validation_error("Ball!") == NOT_ENGLISH
    assert validation_error("Ball_Boy") == NOT_ENGLISH


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_nothing_at_all_is_refused(name: str) -> None:
    assert validation_error(name) == EMPTY


def test_punctuation_alone_is_not_a_name() -> None:
    assert validation_error("'''") == NOT_ENGLISH
    assert validation_error("-") == NOT_ENGLISH


def test_a_name_longer_than_a_row_can_show_is_refused() -> None:
    assert validation_error("A" * MAX_LENGTH) is None
    assert validation_error("A" * (MAX_LENGTH + 1)) == TOO_LONG


def test_surrounding_and_doubled_spaces_do_not_make_a_different_name() -> None:
    assert normalise("  Big   Boy ") == "Big Boy"
    assert validation_error("  Big   Boy ") is None


def test_a_trailing_space_does_not_sneak_a_second_member_past_the_check() -> None:
    """Two rows reading "Ball" and "Ball " look identical on screen."""
    assert normalise("Ball ") == normalise("Ball")
