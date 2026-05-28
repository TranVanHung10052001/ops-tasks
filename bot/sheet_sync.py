"""
Google Sheet KPI Sync — pulls daily KPI metrics from a manager-maintained Google Sheet
and stores them in the bot's `metrics` table.

Runs every 30 minutes via APScheduler (registered in main.py).
Drop-in alternative / supplement to redash_sync.py — pick whichever data source is easier.

== Two auth modes ==

Mode A — Service Account (recommended for production):
  1. Create a Google Cloud service account at console.cloud.google.com
  2. Enable Google Sheets API for the project
  3. Download JSON credentials
  4. Share your sheet with the service-account email (Viewer access)
  5. Set GSHEET_SERVICE_ACCOUNT_JSON to either:
     - Absolute or relative path to the JSON file
     - Inline JSON content (single-line, properly escaped)
  6. Set GSHEET_ID to the long ID in the sheet URL

Mode B — Public sheets (no auth):
  1. Share > "Anyone with the link" > Viewer
  2. Set GSHEET_ID
  3. Bot reads via /export?format=csv (no service account needed)

== Sheet structure ==

First row = column headers. Each subsequent row = one day's snapshot.
Bot picks the row with the most recent date in the first column.

Default header → metric mapping (case + diacritic insensitive):

  Ngày                  -> (date column, used to pick latest row — not stored)
  GSV_hôm_nay_tỷ        -> gsv_today_b           (tỷ VNĐ)
  Đơn_hôm_nay           -> orders_today          (count)
  FR_Core_%             -> fill_rate_core_pct
  FR_HAN_%              -> fill_rate_han_pct
  FR_SGN_%              -> fill_rate_sgn_pct
  FR_SME_%              -> fill_rate_sme_pct
  FR_EXP_%              -> fill_rate_exp_pct     (KCN / tỉnh — Bình Dương, Long An…)
  COGS_Bulky_%          -> cogs_bulky_pct
  Driver_Active         -> active_drivers
  Ghi_chú               -> kpi_note

Add custom columns? Extend COLUMN_ALIASES below — bot will silently skip unknown columns.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import unicodedata
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

GSHEET_ID = os.getenv("GSHEET_ID", "").strip()
GSHEET_TAB = os.getenv("GSHEET_TAB", "0").strip()  # gid (digit string) or worksheet name
GSHEET_SERVICE_ACCOUNT_JSON = os.getenv("GSHEET_SERVICE_ACCOUNT_JSON", "").strip()


# Header (normalized: lowercase, no diacritics, spaces→underscore) → bot metric key
COLUMN_ALIASES: dict[str, str] = {
    # Date column — used to pick latest row, NOT stored as a metric
    "ngay":               "_date",
    "date":               "_date",
    # GSV
    "gsv_hom_nay_ty":     "gsv_today_b",
    "gsv":                "gsv_today_b",
    "gsv_today":          "gsv_today_b",
    "gsv_today_b":        "gsv_today_b",
    "gsv_wow_pct":        "gsv_wow_pct",
    "gsv_wow_%":          "gsv_wow_pct",
    # Orders
    "don_hom_nay":        "orders_today",
    "orders":             "orders_today",
    "orders_today":       "orders_today",
    "orders_wow_pct":     "orders_wow_pct",
    "orders_wow_%":       "orders_wow_pct",
    # Fill Rate
    "fr_core_%":          "fill_rate_core_pct",
    "fr_core":            "fill_rate_core_pct",
    "fill_rate_core_pct": "fill_rate_core_pct",
    "fr_han_%":           "fill_rate_han_pct",
    "fr_han":             "fill_rate_han_pct",
    "fill_rate_han_pct":  "fill_rate_han_pct",
    "fr_sgn_%":           "fill_rate_sgn_pct",
    "fr_sgn":             "fill_rate_sgn_pct",
    "fill_rate_sgn_pct":  "fill_rate_sgn_pct",
    "fr_sme_%":           "fill_rate_sme_pct",
    "fr_sme":             "fill_rate_sme_pct",
    "fill_rate_sme_pct":  "fill_rate_sme_pct",
    "fr_exp_%":           "fill_rate_exp_pct",
    "fr_exp":             "fill_rate_exp_pct",
    "fill_rate_exp_pct":  "fill_rate_exp_pct",
    "fr_vsip_%":          "fill_rate_vsip_pct",
    "fr_vsip":            "fill_rate_vsip_pct",
    "fr_songthan_%":      "fill_rate_songthan_pct",
    "fr_longhau_%":       "fill_rate_longhau_pct",
    # COGS
    "cogs_bulky_%":       "cogs_bulky_pct",
    "cogs_bulky":         "cogs_bulky_pct",
    "cogs":               "cogs_bulky_pct",
    "cogs_wow_pct":       "cogs_wow_pct",
    "cogs_wow_%":         "cogs_wow_pct",
    # Drivers
    "driver_active":      "active_drivers",
    "active_drivers":     "active_drivers",
    "drivers":            "active_drivers",
    "driver_station_pct": "driver_station_pct",
    "driver_core_pct":    "driver_core_pct",
    "driver_hub_pct":     "driver_hub_pct",
    "driver_mass_pct":    "driver_mass_pct",
    # Meta / note
    "ghi_chu":            "kpi_note",
    "note":               "kpi_note",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _normalize_header(header: str) -> str:
    """Lowercase, strip Vietnamese diacritics, replace spaces with underscore.
    Used to make column matching robust against minor sheet edits.
    """
    if not header:
        return ""
    s = unicodedata.normalize("NFD", str(header).strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "_")


def _map_header(header: str) -> str | None:
    """Return bot metric key for a sheet column header, or None if unmapped."""
    norm = _normalize_header(header)
    if not norm:
        return None
    return COLUMN_ALIASES.get(norm)


def _clean_value(raw) -> str:
    """Normalize a cell value for storage — strip thousand separators on numerics."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    # Strip thousand separator (VN convention: comma or dot — be careful)
    # Only collapse commas if the result looks numeric.
    stripped = s.replace(",", "")
    try:
        float(stripped)
        return stripped
    except ValueError:
        return s


def _parse_date(s: str) -> datetime:
    """Try common VN date formats. Returns datetime.min on failure (so row sorts last)."""
    s = (s or "").strip()
    if not s:
        return datetime.min
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.min


def _pick_latest_row(mapped_rows: list[dict]) -> dict | None:
    """Pick the row with the most recent _date. Falls back to last non-empty row."""
    if not mapped_rows:
        return None
    valid = [r for r in mapped_rows
             if r.get("_date") and any(v for k, v in r.items() if k != "_date")]
    if not valid:
        # No dated rows — return last row that has any data
        non_empty = [r for r in mapped_rows if any(v for k, v in r.items() if k != "_date")]
        return non_empty[-1] if non_empty else None
    return max(valid, key=lambda r: _parse_date(r.get("_date", "")))


def _rows_to_mapped(rows: list[dict]) -> list[dict]:
    """Convert raw header→value rows into mapped metric_key→value rows."""
    out: list[dict] = []
    for raw_row in rows:
        m: dict = {}
        for header, value in raw_row.items():
            key = _map_header(str(header))
            if key:
                m[key] = _clean_value(value)
        if m:
            out.append(m)
    return out


# ─── Fetchers (service account preferred, CSV fallback) ──────────────────────

async def _fetch_via_service_account() -> list[dict]:
    """Fetch sheet rows using gspread + service account JSON. Returns [] on failure."""
    if not GSHEET_SERVICE_ACCOUNT_JSON:
        return []

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning(
            "gspread/google-auth not installed — "
            "run: pip install gspread google-auth. Falling back to CSV export."
        )
        return []

    try:
        raw = GSHEET_SERVICE_ACCOUNT_JSON
        if raw.lstrip().startswith("{"):
            creds_dict = json.loads(raw)
        else:
            p = Path(raw)
            if not p.exists():
                logger.error("GSHEET_SERVICE_ACCOUNT_JSON file not found: %s", p)
                return []
            creds_dict = json.loads(p.read_text(encoding="utf-8"))

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)

        if GSHEET_TAB.isdigit():
            target_gid = int(GSHEET_TAB)
            ws = next((w for w in sh.worksheets() if w.id == target_gid), sh.sheet1)
        else:
            ws = sh.worksheet(GSHEET_TAB) if GSHEET_TAB else sh.sheet1

        return ws.get_all_records()
    except Exception as e:
        logger.error("Service-account sheet fetch failed: %s", e)
        return []


async def _fetch_via_csv_export() -> list[dict]:
    """Fetch public sheet via /export?format=csv (no auth)."""
    if not GSHEET_ID:
        return []
    gid = GSHEET_TAB if GSHEET_TAB.isdigit() else "0"
    url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv&gid={gid}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            return list(reader)
    except Exception as e:
        logger.warning("CSV-export sheet fetch failed: %s", e)
        return []


# ─── Main entry ──────────────────────────────────────────────────────────────

async def sync_all() -> int:
    """
    Pull the most recent row from the Google Sheet and upsert each mapped metric.
    Returns count of metrics written. Silent no-op when GSHEET_ID is unset.
    """
    if not GSHEET_ID:
        logger.debug("GSHEET_ID not set — skipping sheet sync")
        return 0

    rows: list[dict] = []
    if GSHEET_SERVICE_ACCOUNT_JSON:
        rows = await _fetch_via_service_account()
    if not rows:
        rows = await _fetch_via_csv_export()

    if not rows:
        logger.debug("Sheet sync: no rows fetched (sheet empty or unreachable)")
        return 0

    mapped = _rows_to_mapped(rows)
    latest = _pick_latest_row(mapped)
    if not latest:
        logger.debug("Sheet sync: no usable rows after mapping (check headers)")
        return 0

    from store import upsert_metric
    count = 0
    for key, value in latest.items():
        if key == "_date" or value == "":
            continue
        upsert_metric(key, value, source="gsheet")
        count += 1

    logger.info(
        "Sheet sync: %d metrics updated (row dated %s)",
        count, latest.get("_date", "?"),
    )
    return count
