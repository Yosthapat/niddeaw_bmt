"""Makes a thumbnail for every receipt and slip already in the bucket.

The expenses and revenue screens draw each receipt as a 56px square. New
uploads now store a 200px thumbnail beside the full image, so the list
paints from that; this is the one-off for everything uploaded before, whose
rows still download the full-size receipt — up to 5MB each — to fill the
same square.

The receipts themselves are not touched. The point of photographing one is
reading the small print back off it, so the full image stays exactly as it
is and is still what opens when you tap the thumbnail.

    # see what it would do, change nothing
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        backend/.venv/bin/python tools/thumb_receipts.py

    # do it
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        backend/.venv/bin/python tools/thumb_receipts.py --apply

Running it twice is harmless: a receipt that already has its thumbnail is
skipped. Needs the backend's own environment (backend/.venv).
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.services.receipt_maintenance import make_thumbnails  # noqa: E402


def human(num_bytes: int) -> str:
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.0f} KB"
    return f"{num_bytes / 1048576:.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write; without it nothing is uploaded",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    from supabase import create_client

    report = make_thumbnails(create_client(url, key), apply=args.apply)

    for row in report.rows:
        if row.status == "failed":
            print(f"   ! {row.label:24} {row.detail}")
        elif row.status == "already":
            print(f"   = {row.label:24} has a thumbnail already")
        else:
            mark = "->" if args.apply else ".."
            print(
                f"  {mark} {row.label:24} "
                f"{human(row.before_bytes)} -> {human(row.after_bytes)} thumbnail"
            )

    print(
        f"\n{report.made} to make, {report.already} already there, {report.failed} failed\n"
        f"what the expenses and revenue lists download: "
        f"{human(report.before_total)} -> {human(report.after_total)}"
    )
    if not args.apply and report.made:
        print("\nnothing was written — re-run with --apply")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
