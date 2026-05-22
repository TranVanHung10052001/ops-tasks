"""
Redash Sync — pulls daily KPIs from Redash REST API and stores in SQLite metrics table.
Runs every 30 minutes via APScheduler (registered in main.py).

== Redash query setup ==

Option A — Single combined query (recommended):
  Set REDASH_QUERY_METRICS to your query ID.
  Query must return rows with columns: metric_key (TEXT), value (TEXT/NUMERIC)
  Example SQL:
      SELECT 'gsv_today_b'        AS metric_key, ROUND(SUM(gsv)/1e9, 2)::TEXT AS value
        FROM truck_daily WHERE date = CURRENT_DATE
      UNION ALL
      SELECT 'orders_today',      COUNT(*)::TEXT
        FROM truck_daily WHERE date = CURRENT_DATE
      UNION ALL
      SELECT 'fill_rate_core_pct', ROUND(AVG(fill_rate_core)*100, 1)::TEXT
        FROM truck_daily WHERE date = CURRENT_DATE
      -- ... etc

Option B — Individual queries per metric (fallback):
  Set REDASH_QUERY_GSV_TODAY, REDASH_QUERY_ORDERS_TODAY, etc.
  Each query must return 1 row with a column named "value".

== Metric keys supported by dashboard ==
  gsv_today_b          float — "8.7"  (tỷ VNĐ)
  gsv_wow_pct          float — "12.0" (% week-over-week, positive = up)
  orders_today         int   — "1247"
  orders_wow_pct       float — "9.0"
  fill_rate_core_pct   float — "78.0" (%)
  fill_rate_han_pct    float — "74.0"
  fill_rate_sgn_pct    float — "68.0"
  fill_rate_vsip_pct   float — "84.0"
  fill_rate_songthan_pct float — "71.0"
  fill_rate_longhau_pct  float — "79.0"
  cogs_bulky_pct       float — "28.4" (%)
  cogs_wow_pct         float — "-0.5" (negative = improved)
  active_drivers       int   — "1847"
  driver_station_pct   int   — "18"   (% of total fleet)
  driver_core_pct      int   — "31"
  driver_hub_pct       int   — "28"
  driver_mass_pct      int   — "23"
"""

import logging
import os

logger = logging.getLogger(__name__)

REDASH_URL = os.getenv("REDASH_URL", "")
REDASH_API_KEY = os.getenv("REDASH_API_KEY", "")
REDASH_QUERY_METRICS = os.getenv("REDASH_QUERY_METRICS", "")

# Individual fallback query IDs (leave empty to skip)
_INDIVIDUAL_QUERIES: dict[str, str] = {
    "gsv_today_b":             os.getenv("REDASH_QUERY_GSV_TODAY", ""),
    "gsv_wow_pct":             os.getenv("REDASH_QUERY_GSV_WOW", ""),
    "orders_today":            os.getenv("REDASH_QUERY_ORDERS_TODAY", ""),
    "orders_wow_pct":          os.getenv("REDASH_QUERY_ORDERS_WOW", ""),
    "fill_rate_core_pct":      os.getenv("REDASH_QUERY_FR_CORE", ""),
    "fill_rate_han_pct":       os.getenv("REDASH_QUERY_FR_HAN", ""),
    "fill_rate_sgn_pct":       os.getenv("REDASH_QUERY_FR_SGN", ""),
    "fill_rate_vsip_pct":      os.getenv("REDASH_QUERY_FR_VSIP", ""),
    "fill_rate_songthan_pct":  os.getenv("REDASH_QUERY_FR_SONGTHAN", ""),
    "fill_rate_longhau_pct":   os.getenv("REDASH_QUERY_FR_LONGHAU", ""),
    "cogs_bulky_pct":          os.getenv("REDASH_QUERY_COGS_BULKY", ""),
    "cogs_wow_pct":            os.getenv("REDASH_QUERY_COGS_WOW", ""),
    "active_drivers":          os.getenv("REDASH_QUERY_ACTIVE_DRIVERS", ""),
    "driver_station_pct":      os.getenv("REDASH_QUERY_DRIVER_STATION", ""),
    "driver_core_pct":         os.getenv("REDASH_QUERY_DRIVER_CORE", ""),
    "driver_hub_pct":          os.getenv("REDASH_QUERY_DRIVER_HUB", ""),
    "driver_mass_pct":         os.getenv("REDASH_QUERY_DRIVER_MASS", ""),
}


async def _fetch_query(query_id: str) -> list[dict]:
    """Fetch latest cached result for a Redash query (no re-run)."""
    if not REDASH_URL or not REDASH_API_KEY or not query_id:
        return []
    url = f"{REDASH_URL.rstrip('/')}/api/queries/{query_id}/results"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Key {REDASH_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("query_result", {}).get("data", {}).get("rows", [])
    except Exception as e:
        logger.warning("Redash fetch query %s failed: %s", query_id, e)
        return []


async def sync_all() -> int:
    """
    Sync all metrics from Redash. Returns count of metrics written.
    Safe to call even if Redash is not configured (returns 0 silently).
    """
    if not REDASH_URL or not REDASH_API_KEY:
        logger.debug("Redash not configured — skipping sync")
        return 0

    from store import upsert_metric
    updated = 0

    # Option A: combined query
    if REDASH_QUERY_METRICS:
        rows = await _fetch_query(REDASH_QUERY_METRICS)
        for row in rows:
            key = row.get("metric_key") or row.get("key")
            val = row.get("value") or row.get("metric_value")
            if key and val is not None:
                upsert_metric(str(key), str(val), source="redash")
                updated += 1
        if updated > 0:
            logger.info("Redash sync (combined): %d metrics updated", updated)
            return updated

    # Option B: individual queries
    for metric_key, query_id in _INDIVIDUAL_QUERIES.items():
        if not query_id:
            continue
        rows = await _fetch_query(query_id)
        if not rows:
            continue
        first = rows[0]
        # Accept column named "value", the metric key itself, or the first column
        val = (
            first.get("value")
            or first.get("metric_value")
            or first.get(metric_key)
            or (list(first.values())[0] if first else None)
        )
        if val is not None:
            upsert_metric(metric_key, str(val), source="redash")
            updated += 1

    if updated > 0:
        logger.info("Redash sync (individual): %d metrics updated", updated)
    else:
        logger.debug("Redash sync: no data returned from any query")
    return updated
