"""
Incident data canonicalization and serialization.
Used by process_site to normalize detector outputs.
"""
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def canonize_incident(inc: dict, site_id: str) -> dict:
    """Normalize incident keys & types for downstream UI."""
    inc = dict(inc) if not isinstance(inc, dict) else inc

    # Timestamps: accept legacy 'start_day'/'last_day'
    st = inc.get("start_time", inc.get("start_day"))
    et = inc.get("end_time", inc.get("last_day", st))

    try:
        st = pd.to_datetime(st) if st is not None else None
    except Exception:
        st = None
    try:
        et = pd.to_datetime(et) if et is not None else st
    except Exception:
        et = st

    inc["start_time"] = st
    inc["end_time"] = et

    # Alert date: if missing, derive from days_needed
    if inc.get("alert_date") is None and st is not None:
        dn = inc.get("days_needed")
        try:
            dn = int(dn) if dn is not None else None
        except Exception:
            dn = None
        if dn and dn > 0:
            inc["alert_date"] = st.normalize() + pd.Timedelta(days=dn - 1)
        else:
            inc["alert_date"] = et.normalize() if et is not None else st.normalize()

    # Stable event_id (site__YYYY-MM-DD__YYYY-MM-DD)
    if not inc.get("event_id") and st is not None:
        st_d = st.date()
        et_d = et.date() if et is not None else st_d
        inc["event_id"] = f"{site_id}__{st_d}__{et_d}"

    # Coerce common numeric fields
    for num_key in ("confidence", "max_deltaNF", "volume_lost_kL"):
        if num_key in inc and inc[num_key] is not None:
            try:
                inc[num_key] = float(inc[num_key])
            except Exception:
                pass

    # Ensure status exists
    if "status" not in inc or inc["status"] is None:
        inc["status"] = inc.get("status", "UNKNOWN")

    return inc


def canonize_confirmed_df(df_in: pd.DataFrame, site_id: str) -> pd.DataFrame:
    """Add start_time/end_time/event_id columns if missing and ensure Timestamp types."""
    if df_in is None or len(df_in) == 0:
        return pd.DataFrame()

    out = df_in.copy()

    # start_time / end_time from legacy fields if needed
    if "start_time" not in out.columns and "start_day" in out.columns:
        out.loc[:, "start_time"] = pd.to_datetime(out["start_day"], errors="coerce")
    elif "start_time" in out.columns:
        out.loc[:, "start_time"] = pd.to_datetime(out["start_time"], errors="coerce")

    if "end_time" not in out.columns and "last_day" in out.columns:
        out.loc[:, "end_time"] = pd.to_datetime(out["last_day"], errors="coerce")
    elif "end_time" in out.columns:
        out.loc[:, "end_time"] = pd.to_datetime(out["end_time"], errors="coerce")

    # alert_date if present
    if "alert_date" in out.columns:
        out.loc[:, "alert_date"] = pd.to_datetime(out["alert_date"], errors="coerce")

    # event_id stable
    if "event_id" not in out.columns:
        def _mk_eid(row):
            st = row.get("start_time")
            et = row.get("end_time") if pd.notna(row.get("end_time")) else row.get("start_time")
            try:
                sd = pd.to_datetime(st).date()
            except Exception:
                sd = None
            try:
                ed = pd.to_datetime(et).date() if et is not None else sd
            except Exception:
                ed = sd
            if sd is None:
                return f"{site_id}__unknown__unknown"
            return f"{site_id}__{sd}__{ed}"

        out.loc[:, "event_id"] = [_mk_eid(out.loc[i, :].to_dict()) for i in out.index]

    return out


def to_dashboard_dict(incident: dict) -> dict:
    """Return incident dict with serializable types for dashboard UI."""
    return {
        "site_id": incident["site_id"],
        "status": incident.get("status", ""),
        "start_day": pd.to_datetime(incident["start_day"]),
        "last_day": pd.to_datetime(incident["last_day"]),
        "severity_max": incident.get("severity_max", "S1"),
        "confidence": float(incident.get("confidence", 0)),
        "volume_lost_kL": float(incident.get("volume_lost_kL", 0)),
        "reason_codes": list(incident.get("reason_codes", [])),
        "alert_date": pd.to_datetime(incident.get("alert_date", incident["last_day"])),
    }
