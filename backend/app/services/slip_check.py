"""Reading the QR on a transfer slip, and saying whether it was used before.

Thai bank slips carry a small QR (the Bank of Thailand's slip format): an
EMV-style string whose tag 00 holds the sending bank's code (sub-tag 01)
and the transfer's reference (sub-tag 02), then the country (51) and a
CRC (91). The reference is what makes a slip one transfer: the same one on
a second bill, top-up or order is the same money shown twice.

This checks nothing with any bank. A slip made up from nothing, with a QR
made up to match, reads as new; only a slip-verification service can tell
that. What it does catch, free, is a real slip shown again, and an image
with no slip QR on it at all.

Reading never stops an upload: a slip that can't be read is kept and shown
to the admin as "no QR", as it would have been before this existed.
"""

import io
import logging
from dataclasses import dataclass
from typing import Any, Literal

from PIL import Image, ImageOps
from supabase import Client

from app.db_utils import rows

log = logging.getLogger(__name__)

TABLE = "slip_checks"
Kind = Literal["bill", "topup", "order"]


@dataclass(frozen=True)
class SlipQr:
    found: bool
    ref: str | None = None
    bank: str | None = None


def _tlv(data: str) -> dict[str, str] | None:
    """Tag-length-value pairs (2-digit tag, 2-digit length), or None if the
    string doesn't parse cleanly as them."""
    out: dict[str, str] = {}
    i = 0
    while i < len(data):
        if i + 4 > len(data) or not data[i : i + 4].isdigit():
            return None
        tag, size = data[i : i + 2], int(data[i + 2 : i + 4])
        value = data[i + 4 : i + 4 + size]
        if len(value) != size:
            return None
        out[tag] = value
        i += 4 + size
    return out


def parse(payload: str) -> SlipQr:
    """What a QR's text says, if it is a bank slip's."""
    top = _tlv(payload.strip())
    inner = _tlv(top["00"]) if top and "00" in top else None
    ref = (inner or {}).get("02", "").strip()
    if not inner or not ref or not 4 <= len(ref) <= 64:
        return SlipQr(found=True)
    bank = inner.get("01", "").strip()
    return SlipQr(found=True, ref=ref, bank=bank if len(bank) == 3 and bank.isdigit() else None)


def read(image: bytes) -> SlipQr:
    """The slip QR in an image, or found=False if there is no QR at all."""
    try:
        import zxingcpp
    except ImportError:  # pragma: no cover — only if the wheel is missing
        log.warning("zxing-cpp is not installed; slips are not read")
        return SlipQr(found=False)
    try:
        with Image.open(io.BytesIO(image)) as source:
            picture = ImageOps.exif_transpose(source).convert("RGB")
            texts = [r.text for r in zxingcpp.read_barcodes(picture)]
    except Exception:  # noqa: BLE001 — a picture we can't read is just "no QR"
        return SlipQr(found=False)
    if not texts:
        return SlipQr(found=False)
    # a slip QR beats any other QR in the picture (a shop logo, a PromptPay code)
    parsed = [parse(t) for t in texts]
    return next((p for p in parsed if p.ref), parsed[0])


def record(supabase: Client, kind: Kind, target_id: str, slip_url: str, *images: bytes) -> SlipQr:
    """Read the slip just attached to this bill / top-up / order and keep
    what it said, in place of what an earlier slip for it said. Tries each
    image given (the upload as sent, then as stored) until one reads.

    Never raises: a member's upload must not fail because of this."""
    got = SlipQr(found=False)
    try:
        for image in images:
            got = read(image)
            if got.ref:
                break
        supabase.table(TABLE).upsert(
            {
                "kind": kind,
                "target_id": str(target_id),
                "slip_url": slip_url,
                "qr_found": got.found,
                "qr_ref": got.ref,
                "bank_code": got.bank,
            },
            on_conflict="kind,target_id",
        ).execute()
    except Exception:
        log.exception("could not record the slip QR for %s %s", kind, target_id)
    return got


# --- what the admin is told -------------------------------------------------

Status = Literal["ok", "duplicate", "no_qr", "not_slip", "unchecked"]


def _describe(supabase: Client, kind: str, target_id: str) -> dict[str, Any]:
    """Who and what an earlier use of a slip was, for the admin to look at."""
    out: dict[str, Any] = {
        "kind": kind,
        "target_id": target_id,
        "who": None,
        "when": None,
        "amount": None,
        "gone": False,
    }
    table = {"bill": "billings", "topup": "credit_topups", "order": "shop_orders"}[kind]
    found = rows(supabase.table(table).select("*").eq("id", target_id).limit(1).execute())
    if not found:
        out["gone"] = True
        return out
    row = found[0]
    player_id = row.get("player_id")
    if player_id:
        p = rows(
            supabase.table("players").select("nickname").eq("id", str(player_id)).limit(1).execute()
        )
        out["who"] = p[0]["nickname"] if p else None
    else:
        out["who"] = row.get("guest_name")
    if kind == "bill":
        adjusted = row.get("amount_adjusted")
        out["amount"] = float(adjusted if adjusted is not None else row.get("amount_calc") or 0)
        out["when"] = row.get("slip_sent_at") or row.get("updated_at")
    elif kind == "topup":
        out["amount"] = float(row.get("price") or 0)
        out["when"] = row.get("slip_sent_at") or row.get("created_at")
    else:
        out["amount"] = float(row.get("total") or 0)
        out["when"] = row.get("created_at")
    return out


def checks(supabase: Client, kind: str, target_ids: list[str]) -> list[dict[str, Any]]:
    """Per bill / top-up / order: what its slip's QR said, and the first
    other thing the same slip was used for, if any."""
    if not target_ids:
        return []
    mine = {
        str(r["target_id"]): r
        for r in rows(
            supabase.table(TABLE)
            .select("*")
            .eq("kind", kind)
            .in_("target_id", target_ids)
            .execute()
        )
    }
    refs = sorted({str(r["qr_ref"]) for r in mine.values() if r.get("qr_ref")})
    same: dict[str, list[dict[str, Any]]] = {}
    if refs:
        for r in rows(supabase.table(TABLE).select("*").in_("qr_ref", refs).execute()):
            same.setdefault(str(r["qr_ref"]), []).append(r)
    out: list[dict[str, Any]] = []
    for tid in target_ids:
        row = mine.get(tid)
        item: dict[str, Any] = {
            "target_id": tid,
            "status": "unchecked",
            "bank": None,
            "ref": None,
            "used_before": None,
        }
        if row is not None:
            item["bank"] = row.get("bank_code")
            ref = row.get("qr_ref")
            item["ref"] = ref
            if not row.get("qr_found"):
                item["status"] = "no_qr"
            elif not ref:
                item["status"] = "not_slip"
            else:
                others = [
                    o
                    for o in same.get(str(ref), [])
                    if not (o["kind"] == kind and str(o["target_id"]) == tid)
                ]
                if others:
                    # The earliest of the other payments, by when it was paid;
                    # the stored rows' own times are when a slip was read,
                    # which a backfill makes all the same.
                    found = [
                        _describe(supabase, o["kind"], str(o["target_id"])) for o in others[:5]
                    ]
                    found.sort(key=lambda d: (d["when"] is None, str(d["when"] or "")))
                    item["status"] = "duplicate"
                    item["used_before"] = found[0]
                    item["used_count"] = len(others)
                else:
                    item["status"] = "ok"
        out.append(item)
    return out
