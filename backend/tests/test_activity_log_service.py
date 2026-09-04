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
