from typing import Any, cast


def rows(result: Any) -> list[dict[str, Any]]:
    """Casts a postgrest/supabase-py query response's `.data` to a plain list
    of dicts. Centralizes the one spot where we trust the external client's
    untyped response shape, instead of scattering `# type: ignore` everywhere.
    """
    return cast(list[dict[str, Any]], result.data or [])
