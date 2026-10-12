"""The rules a member's nickname has to keep.

Nicknames are what the whole app is read in: match rows, the queue, the
ranking, a bill. Two members called the same thing make every one of those
ambiguous, and there is no second field to tell them apart by.

Three rules, all checked in one place because the admin screen and the
check-in screen both create members and the API is what either of them
ends up calling:

- English letters only, plus an apostrophe, a hyphen and spaces between
  words — the club already has "P'Tee", so the punctuation people really
  use is allowed rather than stripped.
- The first letter is a capital, so a list of members reads as a list of
  names.
- Nobody else already has it, compared without regard to case: "ball" is
  the same person as "Ball" at the side of a court, whatever the database
  thinks.
"""

from __future__ import annotations

import re

# One or more words of letters, apostrophes and hyphens, separated by
# single spaces. The leading [A-Z] is the capital rule; anchors on both
# ends so a name is this and nothing else.
NICKNAME_PATTERN = re.compile(r"^[A-Z][A-Za-z'-]*(?: [A-Za-z'-]+)*$")

MAX_LENGTH = 40

EMPTY = "ต้องใส่ชื่อสมาชิก"
TOO_LONG = f"ชื่อยาวเกินไป (ไม่เกิน {MAX_LENGTH} ตัวอักษร)"
NOT_ENGLISH = "ชื่อต้องเป็นภาษาอังกฤษเท่านั้น (ใช้ ' - และเว้นวรรคได้)"
NOT_CAPITALISED = "ตัวอักษรแรกต้องเป็นตัวพิมพ์ใหญ่"


def normalise(raw: str) -> str:
    """Trim the ends and collapse runs of whitespace to single spaces.

    Applied before both validation and storage, so "  Big   Boy " and
    "Big Boy" are the same name rather than two members whose rows look
    identical on screen.
    """
    return " ".join(raw.split())


def validation_error(raw: str) -> str | None:
    """The reason this nickname is not allowed, or None if it is.

    Returns the message rather than raising: the same function answers the
    router (which turns it into a 400) and a test, and the messages are
    what the admin reads, so they are written for them and not for a log.
    """
    name = normalise(raw)
    if not name:
        return EMPTY
    if len(name) > MAX_LENGTH:
        return TOO_LONG
    if NICKNAME_PATTERN.match(name):
        return None
    # Past this point the name is rejected; the only question left is which
    # message helps. A name made of allowed characters that simply starts
    # lowercase gets told about the capital, because telling someone their
    # name "must be English" when it already is would send them looking for
    # the wrong thing.
    if re.match(r"^[A-Za-z][A-Za-z'\- ]*$", name):
        return NOT_CAPITALISED
    return NOT_ENGLISH


def taken_message(name: str) -> str:
    return f'มีสมาชิกชื่อ "{name}" อยู่แล้ว'
