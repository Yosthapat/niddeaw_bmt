"""Pure logic for turning an admin write request into a human-readable
activity-log entry — no I/O, fully unit-testable. The middleware
(app/middleware/activity_log.py) does the actual DB write; this module just
decides what to call each request.
"""

import re

LOGGED_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

# (method, Thai label, path regex). Matched in order, first hit wins.
# Unmapped admin write routes still get logged (see describe_action's
# fallback) so a new endpoint added without updating this table is never
# silently dropped from the log — just less nicely labeled until it is.
_ROUTE_LABELS: list[tuple[str, str, re.Pattern[str]]] = [
    ("POST", "สร้าง session", re.compile(r"^/api/admin/sessions$")),
    ("PATCH", "แก้ไข session", re.compile(r"^/api/admin/sessions/[^/]+$")),
    ("DELETE", "ลบ session", re.compile(r"^/api/admin/sessions/[^/]+$")),
    ("POST", "เช็คอิน", re.compile(r"^/api/admin/checkins$")),
    ("POST", "เช็คเอาท์", re.compile(r"^/api/admin/checkins/[^/]+/checkout$")),
    ("POST", "ล็อคคู่", re.compile(r"^/api/admin/matchmaking/locked-pairs$")),
    ("DELETE", "ปลดล็อคคู่", re.compile(r"^/api/admin/matchmaking/locked-pairs/[^/]+$")),
    ("POST", "ยืนยันคู่แข่ง", re.compile(r"^/api/admin/matchmaking/confirm$")),
    ("DELETE", "ยกเลิกแมตช์", re.compile(r"^/api/admin/matchmaking/matches/[^/]+$")),
    ("POST", "บันทึกผลแมตช์", re.compile(r"^/api/admin/matchmaking/matches/[^/]+/result$")),
    ("POST", "ปิดยอด session", re.compile(r"^/api/admin/billing/close-session/[^/]+$")),
    ("POST", "เพิ่มบิลผู้เล่น", re.compile(r"^/api/admin/billing/player/[^/]+/[^/]+$")),
    ("PATCH", "ปรับยอดบิล", re.compile(r"^/api/admin/billing/[^/]+/adjust$")),
    ("PATCH", "เปลี่ยนสถานะจ่ายบิล", re.compile(r"^/api/admin/billing/[^/]+/paid-status$")),
    ("POST", "เพิ่มรายจ่าย", re.compile(r"^/api/admin/expenses$")),
    ("PATCH", "แก้ไขรายจ่าย", re.compile(r"^/api/admin/expenses/[^/]+$")),
    ("DELETE", "ลบรายจ่าย", re.compile(r"^/api/admin/expenses/[^/]+$")),
    ("POST", "ทำจ่ายบิลรายจ่าย", re.compile(r"^/api/admin/expenses/[^/]+/pay$")),
    ("POST", "อัพโหลดใบเสร็จ", re.compile(r"^/api/admin/expenses/[^/]+/receipt$")),
    ("POST", "เพิ่มสมาชิก", re.compile(r"^/api/admin/players$")),
    ("PATCH", "แก้ไขสมาชิก", re.compile(r"^/api/admin/players/[^/]+$")),
    ("POST", "อัพโหลดรูปสมาชิก", re.compile(r"^/api/admin/players/[^/]+/avatar$")),
    ("PUT", "แก้ไขตั้งค่า", re.compile(r"^/api/admin/settings$")),
]


def describe_action(method: str, path: str) -> str:
    for candidate_method, label, pattern in _ROUTE_LABELS:
        if candidate_method == method and pattern.match(path):
            return label
    return f"{method} {path}"
