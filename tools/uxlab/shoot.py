"""Photographs every screen of the built app at one width, logged in as an
admin, against tools/uxlab/lab.py.

    python tools/uxlab/lab.py &
    VITE_API_BASE_URL=http://127.0.0.1:5399 npm --prefix frontend run build
    python tools/uxlab/shoot.py --width 430 --out /tmp/ux

A screen with nothing on it teaches nothing, so lab.py seeds a night in
progress; what lands in --out is what a judgement about this UI has to be
based on.
"""

from __future__ import annotations

import argparse
import http.server
import os
import re
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.abspath(os.path.join(HERE, "..", "..", "frontend", "dist"))
API = os.environ.get("UXLAB_API", "http://127.0.0.1:5399")
STATIC_PORT = int(os.environ.get("UXLAB_STATIC_PORT", "5324"))
BASE = f"http://localhost:{STATIC_PORT}"
PASSWORD = "uxlab"

# Public first, then the admin screens in the order a club night uses them.
SCREENS: list[tuple[str, str]] = [
    ("public_home", "/"),
    ("public_members", "/members"),
    ("public_ranking", "/ranking"),
    ("public_hall_of_fame", "/hall-of-fame"),
    ("public_live", "/live"),
    ("public_matches", "/matches"),
    ("admin_login", "/admin/login"),
    ("admin_dashboard", "/admin"),
    ("admin_checkin", "/admin/checkin"),
    ("admin_members", "/admin/members"),
    ("admin_matchmaking", "/admin/matchmaking"),
    ("admin_billing", "/admin/billing"),
    ("admin_expenses", "/admin/expenses"),
    ("admin_revenue", "/admin/revenue"),
    ("admin_settings", "/admin/settings"),
    ("admin_activity_log", "/admin/activity-log"),
]


def serve_dist() -> None:
    if not os.path.isdir(DIST):
        sys.exit(f"no build at {DIST} — run the vite build first (see the docstring)")
    os.chdir(DIST)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib's name
            path = self.path.split("?")[0]
            # history-mode routes have no file of their own
            if "." not in os.path.basename(path) and not os.path.exists(DIST + path):
                self.path = "/index.html"
            super().do_GET()

        def log_message(self, *args: object) -> None:
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    threading.Thread(
        target=Server(("127.0.0.1", STATIC_PORT), Handler).serve_forever, daemon=True
    ).start()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=430, help="viewport width in px")
    parser.add_argument("--height", type=int, default=932)
    parser.add_argument("--out", default="/tmp/ux")
    parser.add_argument("--locale", default="th", choices=["th", "en"])
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    serve_dist()

    errors: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get("UXLAB_CHROMIUM", "/opt/pw-browsers/chromium")
        )
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height}, device_scale_factor=2
        )
        context.add_init_script(
            f"try{{localStorage.setItem('niddeaw_bmt_locale','{args.locale}');}}catch(e){{}}"
        )
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(f"{page.url}: {str(e)[:160]}"))

        page.goto(f"{BASE}/admin/login", wait_until="load", timeout=30000)
        page.wait_for_timeout(1500)
        page.fill("input[type=text], input:not([type=password]):not([type=search])", "admin")
        page.fill("input[type=password]", PASSWORD)
        page.get_by_role("button", name=re.compile("เข้าสู่ระบบ|Sign in|Log in")).first.click()
        page.wait_for_timeout(2500)
        if "/admin/login" in page.url:
            sys.exit(f"could not log in — is lab.py running on {API}?")

        for name, path in SCREENS:
            page.goto(BASE + path, wait_until="load", timeout=30000)
            page.wait_for_timeout(2200)
            page.screenshot(path=os.path.join(args.out, f"{name}.png"), full_page=True)
            print(f"  {name:24} {path}", flush=True)
        browser.close()

    print(f"\n{len(SCREENS)} screens -> {args.out}")
    if errors:
        print("\npage errors (a UI that throws scores no points for polish):")
        for error in dict.fromkeys(errors):
            print("  " + error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
