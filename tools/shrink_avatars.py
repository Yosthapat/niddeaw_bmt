"""Shrinks the avatars already in the bucket to the size the site draws.

New uploads are resized by the API itself (app/services/image_service.py).
This is for the photos uploaded before that, which are stored at up to
1600px and re-sent to every visitor of the members, ranking and live
pages.

The admin screen has a button that does the same thing (Settings →
ย่อรูปสมาชิก), which is the easier route and needs no keys. This exists
for anyone at a terminal; both call the same function, so neither can
drift from the other.

    # see what it would do, change nothing
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python tools/shrink_avatars.py

    # do it
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python tools/shrink_avatars.py --apply

Needs the backend's own environment (backend/.venv).
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.services.avatar_maintenance import shrink_all  # noqa: E402


def human(num_bytes: int) -> str:
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.0f} KB"
    return f"{num_bytes / 1048576:.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write; without it nothing is uploaded, updated or deleted",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    from supabase import create_client

    report = shrink_all(create_client(url, key), apply=args.apply)

    mark = {"shrunk": "->" if args.apply else "..", "already": " =", "failed": " !"}
    for row in report.rows:
        if row.status == "failed":
            print(f"  {mark[row.status]} {row.nickname:12} {row.detail}")
        elif row.status == "already":
            print(f"  {mark[row.status]} {row.nickname:12} already {human(row.before_bytes)}")
        else:
            saved = row.before_bytes - row.after_bytes
            print(
                f"  {mark[row.status]} {row.nickname:12} "
                f"{human(row.before_bytes)} -> {human(row.after_bytes)}  (saves {human(saved)})"
            )

    print(
        f"\n{report.shrunk} to shrink, {report.already} already done, {report.failed} failed\n"
        f"every page view of the members list: "
        f"{human(report.before_total)} -> {human(report.after_total)}"
    )
    if not args.apply and report.shrunk:
        print("\nnothing was written — re-run with --apply")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
