import pathlib
import re

from app.services import activity_log_service as svc


def test_maps_known_routes_to_thai_labels() -> None:
    assert svc.describe_action("POST", "/api/admin/sessions") == "สร้าง session"
    assert svc.describe_action("PATCH", "/api/admin/sessions/abc-123") == "แก้ไข session"
    assert svc.describe_action("DELETE", "/api/admin/sessions/abc-123") == "ลบ session"
    assert svc.describe_action("POST", "/api/admin/expenses/e1/pay") == "ทำจ่ายบิลรายจ่าย"
    assert svc.describe_action("PUT", "/api/admin/settings") == "แก้ไขตั้งค่า"


def test_falls_back_to_method_and_path_for_unmapped_routes() -> None:
    assert svc.describe_action("POST", "/api/admin/future-thing") == "POST /api/admin/future-thing"


def test_method_mismatch_does_not_match_another_route_s_label() -> None:
    # GET isn't in LOGGED_METHODS and has no mapping of its own — must not
    # accidentally match the POST/PATCH/DELETE session patterns.
    assert svc.describe_action("GET", "/api/admin/sessions") == "GET /api/admin/sessions"


def test_logged_methods_excludes_reads() -> None:
    assert "GET" not in svc.LOGGED_METHODS
    assert {"POST", "PATCH", "PUT", "DELETE"} == svc.LOGGED_METHODS


def test_every_admin_write_route_has_a_label() -> None:
    """The fallback prints a method and a URL — a line nobody reading the
    club's history can use.

    Nine routes had drifted past this table (editing a result among them,
    which is how it was noticed), so the check reads the app's own route
    table rather than a hand-kept copy of it: adding an admin write without
    a label fails here instead of showing up raw on the screen months
    later. It goes through the OpenAPI schema because app.routes nests
    included routers, and how deeply is a FastAPI version's business.
    """
    from app.main import app
    from app.middleware.activity_log import _SKIP_PATHS

    unlabelled: list[str] = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/admin/") or path in _SKIP_PATHS:
            continue
        for method in operations:
            upper = method.upper()
            if upper not in svc.LOGGED_METHODS:
                continue
            # The real request path has values where the template has
            # {names}; the labels match on shape, so any value will do.
            concrete = re.sub(r"\{[^}]+\}", "x", path)
            if svc.describe_action(upper, concrete) == f"{upper} {concrete}":
                unlabelled.append(f"{upper} {path}")

    assert unlabelled == [], f"no Thai label for: {unlabelled}"


def test_the_screen_s_copy_of_this_table_matches_it() -> None:
    """frontend/src/utils/activityAction.ts lists the same routes, because
    the screen reads the label off the method and the path rather than off
    the stored text — that is what puts Thai (or English) on the rows that
    were written before their route had a label.

    Two tables drift. This one is cheap to compare, and when it drifts the
    screen quietly falls back to the stored label, which is the kind of
    wrong nobody notices.
    """
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "utils"
        / "activityAction.ts"
    ).read_text(encoding="utf-8")

    screen = {
        (method, pattern.replace("\\/", "/"))
        # non-greedy up to the closing "$/," — no pattern in the table
        # contains that sequence itself
        for method, pattern in re.findall(r"\['([A-Z]+)', /\^(.+?)\$/,", source)
    }
    service = {
        (method, pattern.pattern.removeprefix("^").removesuffix("$"))
        for method, _label, pattern in svc._ROUTE_LABELS
    }

    assert screen == service, (
        f"only in the screen: {sorted(screen - service)}; "
        f"only in the service: {sorted(service - screen)}"
    )
