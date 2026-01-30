# false_alarm_patterns.py
# -*- coding: utf-8 -*-
"""
False Alarm Pattern Recording and Matching System

This module provides functionality to:
1. Record false alarm patterns when users mark events as "Ignore"
2. Store patterns with their fingerprints (signals, timing, recurrence)
3. Match new incidents against known patterns
4. Auto-suppress or flag incidents that match known false alarm patterns

Pattern Fingerprint includes:
- Site ID
- Category (pool_fill, fire_test, maintenance, etc.)
- Day of week patterns
- Time window
- Detection signal fingerprint
- Recurrence rules
"""
#%%
import os
import json
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from config import log

# ============================================
# CONFIGURATION
# ============================================

# Use absolute path relative to this script's location to avoid CWD issues
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATTERNS_FILE = os.path.join(_SCRIPT_DIR, "False_Alarm_Patterns.csv")
PATTERN_MATCHES_LOG = os.path.join(_SCRIPT_DIR, "Pattern_Matches_Log.csv")

# Matching thresholds
SIGNAL_MATCH_THRESHOLD = 0.7  # 70% signal similarity required
TIME_WINDOW_TOLERANCE_HOURS = 2  # ±2 hours for time matching
CONFIDENCE_DECAY_DAYS = (
    90  # Pattern confidence decays after 90 days without confirmation
)

# Signal weights for fingerprint matching
SIGNAL_WEIGHTS = {
    "mnf": 0.25,
    "cusum": 0.20,
    "afterhrs": 0.15,
    "vol_spike": 0.15,
    "duration": 0.10,
    "weekday": 0.10,
    "time_of_day": 0.05,
}

# ============================================
# STALENESS CLEANUP CONFIGURATION
# ============================================
STALENESS_THRESHOLD_DAYS = 120  # Auto-deactivate after this many days
CONFIDENCE_DECAY_PERIOD_DAYS = 30  # Apply decay every N days inactive
CONFIDENCE_DECAY_RATE = 0.95  # 5% decay per period (multiply by 0.95)
CONFIDENCE_FLOOR = 0.10  # Minimum confidence (10%)
REACTIVATION_CONFIDENCE = 0.50  # Reset to 50% on reactivation

# ============================================
# NSW SCHOOL CALENDAR CONFIGURATION
# ============================================
# Season tags for pattern matching
VALID_SEASON_TAGS = [
    "term_1", "term_2", "term_3", "term_4",  # School terms
    "summer", "winter_break", "autumn_break", "spring_break",  # Holidays
    "any_term", "any_holiday",  # Wildcards
]

# Seasonal boost/penalty factors
SEASON_MATCH_BOOST = 1.20  # +20% boost when season matches
SEASON_MISMATCH_PENALTY = 0.80  # -20% penalty when season doesn't match
SEASON_WILDCARD_BOOST = 1.15  # +15% boost for wildcard matches


def get_nsw_school_calendar() -> Dict[str, Dict[str, Tuple[int, int]]]:
    """
    NSW school calendar with approximate term dates (2024-2027).

    Returns dict with start/end as (month, day) tuples.
    Note: Exact dates vary ±1 week per year; these are typical ranges.
    """
    return {
        "term_1": {"start": (2, 1), "end": (4, 12)},      # Feb 1 - Apr 12
        "term_2": {"start": (4, 28), "end": (7, 5)},      # Apr 28 - Jul 5
        "term_3": {"start": (7, 21), "end": (9, 27)},     # Jul 21 - Sep 27
        "term_4": {"start": (10, 14), "end": (12, 18)},   # Oct 14 - Dec 18
        "summer": {"start": (12, 19), "end": (1, 31)},    # Dec 19 - Jan 31
    }


# ============================================
# ADAPTIVE MNF TOLERANCE CONFIGURATION
# ============================================
# CV-to-tolerance mapping thresholds
CV_TOLERANCE_MAP = [
    (0.10, 0.15),  # CV < 0.10 → ±15% (stable site)
    (0.20, 0.25),  # CV < 0.20 → ±25% (normal site)
    (0.35, 0.40),  # CV < 0.35 → ±40% (variable site)
    (1.00, 0.50),  # CV >= 0.35 → ±50% (noisy, capped)
]

DEFAULT_MNF_TOLERANCE = 0.30  # Default ±30% if insufficient data
MIN_MNF_SAMPLES = 30  # Minimum samples for CV calculation
MNF_HISTORY_DAYS = 90  # Days of history to consider
MAX_MNF_TOLERANCE = 0.50  # Cap at ±50%
MIN_MNF_TOLERANCE = 0.15  # Floor at ±15%


# ============================================
# PATTERN DATA STRUCTURES
# ============================================


def create_pattern_id(site_id: str, category: str, fingerprint: Dict) -> str:
    """Generate a unique pattern ID based on site, category, and fingerprint."""
    data = f"{site_id}_{category}_{json.dumps(fingerprint, sort_keys=True)}"
    return hashlib.md5(data.encode()).hexdigest()[:12].upper()


def create_signal_fingerprint(incident: Dict) -> Dict:
    """
    Extract the signal fingerprint from an incident.

    This captures which detection signals fired and their relative strengths,
    PLUS critical flow rate metrics for accurate pattern matching.
    """
    fingerprint = {
        "signals_active": [],
        "signal_scores": {},
        "mnf_range": None,
        "mnf_value_Lph": None,  # Actual MNF value in Liters per hour
        "avg_flow_rate_Lph": None,  # Average flow rate during incident
        "peak_flow_rate_Lph": None,  # Peak flow rate observed
        "volume_range": None,
        "volume_kL": None,  # Actual volume in kL
        "duration_range": None,
        "duration_hours": None,  # Actual duration
    }

    # Extract subscores if available
    subscores = incident.get("subscores_ui", {}) or incident.get("subscores", {})
    if subscores:
        for signal, score in subscores.items():
            if score and float(score) > 0.1:  # Signal is active if score > 10%
                fingerprint["signals_active"].append(signal)
                fingerprint["signal_scores"][signal] = round(float(score), 2)

    # Extract MNF (Minimum Night Flow) - CRITICAL for flow rate matching
    # Try multiple possible field names
    mnf = None
    for mnf_field in ["mnf_at_confirm_Lph", "avg_mnf_Lph", "mnf_Lph", "mnf", "MNF"]:
        if mnf_field in incident and incident.get(mnf_field):
            try:
                mnf = float(incident[mnf_field])
                break
            except (ValueError, TypeError):
                continue

    if mnf:
        fingerprint["mnf_value_Lph"] = round(mnf, 2)
        fingerprint["mnf_range"] = [round(mnf * 0.7, 2), round(mnf * 1.3, 2)]  # ±30%

    # Extract average flow rate during the incident
    for flow_field in ["avg_flow_Lph", "avg_flow_rate", "mean_flow", "flow_rate"]:
        if flow_field in incident and incident.get(flow_field):
            try:
                fingerprint["avg_flow_rate_Lph"] = round(float(incident[flow_field]), 2)
                break
            except (ValueError, TypeError):
                continue

    # Extract peak flow rate
    for peak_field in ["peak_flow_Lph", "max_flow", "peak_flow"]:
        if peak_field in incident and incident.get(peak_field):
            try:
                fingerprint["peak_flow_rate_Lph"] = round(
                    float(incident[peak_field]), 2
                )
                break
            except (ValueError, TypeError):
                continue

    # Extract volume
    if "volume_kL" in incident:
        vol = incident.get("volume_kL", 0)
        if vol:
            fingerprint["volume_kL"] = round(float(vol), 2)
            fingerprint["volume_range"] = [
                round(float(vol) * 0.5, 2),
                round(float(vol) * 1.5, 2),
            ]  # ±50%

    # Extract duration
    if "duration_hours" in incident:
        dur = incident.get("duration_hours", 0)
        if dur:
            fingerprint["duration_hours"] = round(float(dur), 2)
            fingerprint["duration_range"] = [
                max(0, round(float(dur) - 6, 2)),
                round(float(dur) + 6, 2),
            ]  # ±6 hours

    return fingerprint


def create_time_fingerprint(incident: Dict) -> Dict:
    """
    Extract time-based fingerprint from an incident.

    Captures day of week, time of day patterns for recurring events.
    """
    fingerprint = {
        "days_of_week": [],
        "time_window_start": None,
        "time_window_end": None,
        "typical_duration_hours": None,
    }

    # Parse start date
    start_day = incident.get("start_day")
    if start_day:
        try:
            dt = pd.to_datetime(start_day)
            fingerprint["days_of_week"] = [dt.dayofweek]  # 0=Monday, 6=Sunday
        except Exception:
            pass

    # If we have hourly data, extract time window
    # For now, use defaults that can be overridden by user

    return fingerprint


# ============================================
# SEASONAL PATTERN DETECTION
# ============================================


def detect_school_season(date_obj: datetime) -> str:
    """
    Detect which NSW school season a date falls into.

    Args:
        date_obj: Date to check (datetime or pd.Timestamp)

    Returns:
        Season string: 'term_1', 'term_2', 'term_3', 'term_4', or 'summer'
    """
    if pd.isna(date_obj):
        return "unknown"

    # Convert to datetime if needed
    if hasattr(date_obj, "to_pydatetime"):
        date_obj = date_obj.to_pydatetime()

    month = date_obj.month
    day = date_obj.day

    calendar = get_nsw_school_calendar()

    for season_name, dates in calendar.items():
        start_m, start_d = dates["start"]
        end_m, end_d = dates["end"]

        # Handle year-wrapping seasons (summer: Dec-Jan)
        if start_m > end_m:
            # Dec 19 to Jan 31
            if (month == start_m and day >= start_d) or \
               (month == end_m and day <= end_d) or \
               (month > start_m) or \
               (month < end_m):
                return season_name
        else:
            # Normal range within same year
            if (month > start_m or (month == start_m and day >= start_d)) and \
               (month < end_m or (month == end_m and day <= end_d)):
                return season_name

    # Default fallback - check gaps in calendar (holiday periods)
    # Apr 13-27: autumn_break, Jul 6-20: winter_break, Sep 28 - Oct 13: spring_break
    if month == 4 and 13 <= day <= 27:
        return "autumn_break"
    if month == 7 and 6 <= day <= 20:
        return "winter_break"
    if (month == 9 and day >= 28) or (month == 10 and day <= 13):
        return "spring_break"

    return "term_1"  # Fallback


def is_school_holiday(date_obj: datetime) -> bool:
    """Check if date falls during school holidays."""
    season = detect_school_season(date_obj)
    return season in ["summer", "winter_break", "autumn_break", "spring_break"]


def is_school_term(date_obj: datetime) -> bool:
    """Check if date falls during school term."""
    season = detect_school_season(date_obj)
    return season in ["term_1", "term_2", "term_3", "term_4"]


def calculate_seasonal_similarity(
    incident_date: datetime,
    pattern: Dict,
) -> float:
    """
    Calculate seasonal match between incident and pattern.

    Args:
        incident_date: Date of the incident
        pattern: Pattern dict with season_tags field

    Returns:
        Boost factor: 1.2 (match), 1.0 (neutral), 0.8 (mismatch)
    """
    # Get pattern's season tags
    season_tags = pattern.get("season_tags", [])

    # Parse JSON if string
    if isinstance(season_tags, str):
        try:
            season_tags = json.loads(season_tags) if season_tags else []
        except (json.JSONDecodeError, TypeError):
            season_tags = []

    # No season tags = neutral (pattern applies to all seasons)
    if not season_tags:
        return 1.0

    # Detect incident's season
    incident_season = detect_school_season(incident_date)

    # Check for direct match
    if incident_season in season_tags:
        return SEASON_MATCH_BOOST  # +20% boost

    # Check for wildcard matches
    if "any_term" in season_tags and is_school_term(incident_date):
        return SEASON_WILDCARD_BOOST  # +15% boost for term wildcard

    if "any_holiday" in season_tags and is_school_holiday(incident_date):
        return SEASON_WILDCARD_BOOST  # +15% boost for holiday wildcard

    # Season mismatch - apply penalty
    return SEASON_MISMATCH_PENALTY  # -20% penalty


def apply_seasonal_confidence_boost(
    match_score: float,
    incident_date: datetime,
    pattern: Dict,
) -> float:
    """
    Apply seasonal boost/penalty to match score.

    Args:
        match_score: Original match score (0-1)
        incident_date: Date of incident
        pattern: Pattern dict

    Returns:
        Adjusted score (clamped to 0-1)
    """
    boost_factor = calculate_seasonal_similarity(incident_date, pattern)
    adjusted_score = match_score * boost_factor

    # Clamp to valid range
    return max(0.0, min(1.0, adjusted_score))


# ============================================
# PATTERN STORAGE
# ============================================


def get_patterns_df() -> pd.DataFrame:
    """Load patterns from CSV file with JSON parsing for complex types."""
    if os.path.exists(PATTERNS_FILE):
        try:
            df = pd.read_csv(PATTERNS_FILE)
            # Parse JSON columns (dict types)
            for col in ["signal_fingerprint", "time_fingerprint", "recurrence_rule"]:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: json.loads(x) if pd.notna(x) and x else {}
                    )
            # Parse JSON columns (list types)
            if "season_tags" in df.columns:
                df["season_tags"] = df["season_tags"].apply(
                    lambda x: json.loads(x) if pd.notna(x) and x else []
                )
            return df
        except Exception as e:
            log.error(f"Error loading patterns file: {e}")

    # Return empty DataFrame with schema (includes new seasonal/MNF columns)
    return pd.DataFrame(
        columns=[
            "pattern_id",
            "site_id",
            "category",
            "description",
            "signal_fingerprint",
            "time_fingerprint",
            "recurrence_rule",
            "auto_suppress",
            "confidence",
            "times_matched",
            "times_confirmed_false",
            "times_was_real_leak",
            "created_at",
            "created_by",
            "last_matched_at",
            "last_updated_at",
            "is_active",
            "notes",
            # New columns for seasonal patterns and adaptive MNF
            "season_tags",
            "baseline_term_usage_kL",
            "baseline_holiday_usage_kL",
            "mnf_tolerance_factor",
        ]
    )


def save_patterns_df(df: pd.DataFrame) -> None:
    """Save patterns DataFrame to CSV with JSON serialization for complex types."""
    df_to_save = df.copy()

    # Convert dict/list columns to JSON strings
    json_columns = [
        "signal_fingerprint",
        "time_fingerprint",
        "recurrence_rule",
        "season_tags",  # New column for seasonal patterns
    ]

    for col in json_columns:
        if col in df_to_save.columns:
            df_to_save[col] = df_to_save[col].apply(
                lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
            )

    df_to_save.to_csv(PATTERNS_FILE, index=False)
    log.info(f"Saved {len(df_to_save)} patterns to {PATTERNS_FILE}")


def record_pattern(
    site_id: str,
    event_id: str,
    incident: Dict,
    category: str,
    description: str,
    is_recurring: bool = False,
    recurrence_type: str = None,  # daily, weekly, monthly, yearly
    recurrence_days: List[int] = None,  # [0,1,2...] for days of week
    time_window_start: str = None,  # "06:00"
    time_window_end: str = None,  # "08:00"
    auto_suppress: bool = False,
    notes: str = "",
    user: str = "",
    season_tags: List[str] = None,  # NSW school calendar seasons
) -> Dict:
    """
    Record a new false alarm pattern with optional seasonal and MNF tolerance info.

    Args:
        site_id: Property ID
        event_id: Original event ID that was marked as false alarm
        incident: Full incident data dict
        category: Category of false alarm (pool_fill, fire_test, etc.)
        description: Human-readable description
        is_recurring: Whether this is expected to recur
        recurrence_type: Type of recurrence (daily, weekly, monthly, yearly)
        recurrence_days: Days of week for weekly recurrence
        time_window_start: Expected start time (HH:MM)
        time_window_end: Expected end time (HH:MM)
        auto_suppress: Whether to automatically suppress future matches
        notes: Additional notes
        user: User who recorded the pattern
        season_tags: List of seasonal tags (e.g., ["summer"], ["term_1", "term_2"])

    Returns:
        Dict with pattern_id and success status
    """
    # Create fingerprints
    signal_fp = create_signal_fingerprint(incident)
    time_fp = create_time_fingerprint(incident)

    # Auto-detect season if not provided
    if season_tags is None:
        start_day = incident.get("start_day")
        if start_day:
            try:
                incident_date = pd.to_datetime(start_day)
                detected_season = detect_school_season(incident_date)
                season_tags = [detected_season]
            except Exception:
                season_tags = []
        else:
            season_tags = []

    # Override time fingerprint with user-provided values
    if recurrence_days:
        time_fp["days_of_week"] = recurrence_days
    if time_window_start:
        time_fp["time_window_start"] = time_window_start
    if time_window_end:
        time_fp["time_window_end"] = time_window_end

    # Create recurrence rule
    recurrence_rule = {
        "is_recurring": is_recurring,
        "type": recurrence_type,
        "days_of_week": recurrence_days or time_fp.get("days_of_week", []),
    }

    # Generate pattern ID
    pattern_id = create_pattern_id(site_id, category, signal_fp)

    # Check if similar pattern already exists
    df = get_patterns_df()
    existing = df[(df["site_id"] == site_id) & (df["category"] == category)]

    if not existing.empty:
        # Check signal similarity against ACTIVE patterns first
        active_patterns = existing[existing["is_active"] == True]
        for _, row in active_patterns.iterrows():
            similarity = calculate_signal_similarity(
                signal_fp, row["signal_fingerprint"]
            )
            if similarity > 0.8:  # Very similar pattern exists
                # Update existing pattern instead
                log.info(
                    f"Updating existing pattern {row['pattern_id']} (similarity: {similarity:.2f})"
                )
                df.loc[
                    df["pattern_id"] == row["pattern_id"], "times_confirmed_false"
                ] += 1
                df.loc[df["pattern_id"] == row["pattern_id"], "confidence"] = min(
                    1.0, row["confidence"] + 0.05
                )
                df.loc[df["pattern_id"] == row["pattern_id"], "last_updated_at"] = (
                    datetime.now().isoformat()
                )
                df.loc[df["pattern_id"] == row["pattern_id"], "auto_suppress"] = (
                    auto_suppress
                )
                save_patterns_df(df)
                return {
                    "success": True,
                    "pattern_id": row["pattern_id"],
                    "action": "updated",
                    "message": f"Updated existing pattern {row['pattern_id']}",
                }

        # Check for DEACTIVATED patterns that could be reactivated
        deactivated = existing[existing["is_active"] == False]
        for _, row in deactivated.iterrows():
            similarity = calculate_signal_similarity(
                signal_fp, row["signal_fingerprint"]
            )
            if similarity > 0.7:  # Similar enough to reactivate
                reactivate_stale_pattern(row["pattern_id"])
                log.info(
                    f"Reactivated deactivated pattern {row['pattern_id']} "
                    f"(similarity: {similarity:.2f})"
                )
                return {
                    "success": True,
                    "pattern_id": row["pattern_id"],
                    "action": "reactivated",
                    "message": f"Reactivated pattern {row['pattern_id']}",
                }

    # Create new pattern with seasonal and adaptive MNF support
    new_pattern = {
        "pattern_id": pattern_id,
        "site_id": site_id,
        "category": category,
        "description": description,
        "signal_fingerprint": signal_fp,
        "time_fingerprint": time_fp,
        "recurrence_rule": recurrence_rule,
        "auto_suppress": auto_suppress,
        "confidence": 0.6,  # Initial confidence
        "times_matched": 0,
        "times_confirmed_false": 1,
        "times_was_real_leak": 0,
        "created_at": datetime.now().isoformat(),
        "created_by": user,
        "last_matched_at": None,
        "last_updated_at": datetime.now().isoformat(),
        "is_active": True,
        "notes": notes,
        # Seasonal pattern fields
        "season_tags": season_tags,
        "baseline_term_usage_kL": None,  # Populated by update_pattern_baseline_usage()
        "baseline_holiday_usage_kL": None,  # Populated by update_pattern_baseline_usage()
        # Adaptive MNF tolerance field
        "mnf_tolerance_factor": None,  # Populated by calculate_adaptive_mnf_tolerance()
    }

    df = pd.concat([df, pd.DataFrame([new_pattern])], ignore_index=True)
    save_patterns_df(df)

    log.info(f"Recorded new false alarm pattern: {pattern_id} for site {site_id}")

    return {
        "success": True,
        "pattern_id": pattern_id,
        "action": "created",
        "message": f"Created new pattern {pattern_id}",
    }


# ============================================
# PATTERN MATCHING
# ============================================


def calculate_signal_similarity(
    fp1: Dict, fp2: Dict, mnf_tolerance: float = None
) -> float:
    """
    Calculate similarity between two signal fingerprints using weighted feature matching.

    NOTE: This is RULE-BASED similarity matching, NOT machine learning.
    It uses:
    - Jaccard similarity for signal sets
    - Adaptive MNF tolerance based on site variability
    - Range overlap calculations for numeric features
    - Weighted aggregation of all similarity scores

    Args:
        fp1: First fingerprint (typically pattern)
        fp2: Second fingerprint (typically incident)
        mnf_tolerance: Optional override for MNF tolerance (uses adaptive if None)

    Returns value between 0.0 (no match) and 1.0 (perfect match).
    """
    if not fp1 or not fp2:
        return 0.0

    score = 0.0
    weights_used = 0.0

    # Compare active signals (Jaccard similarity)
    signals1 = set(fp1.get("signals_active", []))
    signals2 = set(fp2.get("signals_active", []))

    if signals1 or signals2:
        intersection = len(signals1 & signals2)
        union = len(signals1 | signals2)
        if union > 0:
            signal_sim = intersection / union
            score += signal_sim * 0.30  # 30% weight for signal type match
            weights_used += 0.30

    # Compare signal scores (intensity matching)
    scores1 = fp1.get("signal_scores", {})
    scores2 = fp2.get("signal_scores", {})

    if scores1 and scores2:
        common_signals = set(scores1.keys()) & set(scores2.keys())
        if common_signals:
            score_diffs = [abs(scores1[s] - scores2[s]) for s in common_signals]
            avg_diff = sum(score_diffs) / len(score_diffs)
            score_sim = max(0, 1 - avg_diff)  # 0 diff = 1.0, 1.0 diff = 0.0
            score += score_sim * 0.20  # 20% weight for signal intensity match
            weights_used += 0.20

    # Compare MNF using ADAPTIVE tolerance (site-specific ranges)
    # Uses calculate_mnf_similarity_adaptive for smarter matching
    mnf_sim = calculate_mnf_similarity_adaptive(fp1, fp2, mnf_tolerance)
    score += mnf_sim * 0.20  # 20% weight for flow rate match
    weights_used += 0.20

    # Compare volume range
    vol1 = fp1.get("volume_range")
    vol2 = fp2.get("volume_range")
    if vol1 and vol2:
        overlap = max(0, min(vol1[1], vol2[1]) - max(vol1[0], vol2[0]))
        total_range = max(vol1[1], vol2[1]) - min(vol1[0], vol2[0])
        if total_range > 0:
            vol_sim = overlap / total_range
            score += vol_sim * 0.15  # 15% weight for volume match
            weights_used += 0.15

    # Compare duration range
    dur1 = fp1.get("duration_range")
    dur2 = fp2.get("duration_range")
    if dur1 and dur2:
        overlap = max(0, min(dur1[1], dur2[1]) - max(dur1[0], dur2[0]))
        total_range = max(dur1[1], dur2[1]) - min(dur1[0], dur2[0])
        if total_range > 0:
            dur_sim = overlap / total_range
            score += dur_sim * 0.15  # 15% weight for duration match
            weights_used += 0.15

    # Normalize by weights used
    if weights_used > 0:
        return score / weights_used

    return 0.0


def calculate_time_similarity(incident: Dict, pattern: Dict) -> float:
    """
    Calculate time-based similarity between an incident and a pattern.

    Returns value between 0.0 (no match) and 1.0 (perfect match).
    """
    time_fp = pattern.get("time_fingerprint", {})
    recurrence = pattern.get("recurrence_rule", {})

    if not time_fp and not recurrence:
        return 0.5  # Neutral if no time pattern defined

    score = 0.0
    weights_used = 0.0

    # Check day of week match
    incident_start = incident.get("start_day")
    pattern_days = time_fp.get("days_of_week", []) or recurrence.get("days_of_week", [])

    if incident_start and pattern_days:
        try:
            incident_dow = pd.to_datetime(incident_start).dayofweek
            if incident_dow in pattern_days:
                score += 0.5
            weights_used += 0.5
        except Exception:
            pass

    # Check time window match (if we have time data)
    time_start = time_fp.get("time_window_start")
    time_end = time_fp.get("time_window_end")

    if time_start and time_end:
        # For now, give partial credit if time window is defined
        # In future, compare actual incident time
        score += 0.25
        weights_used += 0.5

    if weights_used > 0:
        return score / weights_used

    return 0.5


def match_incident_to_patterns(
    incident: Dict,
    site_id: str = None,
) -> List[Dict]:
    """
    Match an incident against all known false alarm patterns.

    Includes seasonal similarity scoring based on NSW school calendar.

    Args:
        incident: Incident data dict
        site_id: Optional site ID to filter patterns

    Returns:
        List of matching patterns with match scores, sorted by relevance
    """
    df = get_patterns_df()

    if df.empty:
        return []

    # Filter by site if provided
    if site_id:
        # Include site-specific patterns and any "global" patterns
        df = df[(df["site_id"] == site_id) | (df["site_id"] == "ALL")]

    # Only consider active patterns
    df = df[df["is_active"] == True]

    if df.empty:
        return []

    # Create fingerprint for the incident
    incident_fp = create_signal_fingerprint(incident)

    # Get incident date for seasonal matching
    incident_date = None
    start_day = incident.get("start_day")
    if start_day:
        try:
            incident_date = pd.to_datetime(start_day)
        except Exception:
            pass

    matches = []

    for _, pattern in df.iterrows():
        # Get pattern's MNF tolerance (adaptive, site-specific)
        mnf_tolerance = pattern.get("mnf_tolerance_factor")
        if pd.isna(mnf_tolerance) or mnf_tolerance is None:
            mnf_tolerance = DEFAULT_MNF_TOLERANCE
        else:
            mnf_tolerance = float(mnf_tolerance)

        # Calculate signal similarity with adaptive MNF tolerance
        signal_sim = calculate_signal_similarity(
            incident_fp, pattern["signal_fingerprint"], mnf_tolerance=mnf_tolerance
        )

        # Calculate time similarity
        time_sim = calculate_time_similarity(incident, pattern)

        # Calculate seasonal similarity boost/penalty
        seasonal_boost = 1.0
        if incident_date:
            seasonal_boost = calculate_seasonal_similarity(incident_date, pattern)

        # Combined score (weighted) - this is the RAW match quality
        combined_score = (signal_sim * 0.7) + (time_sim * 0.3)

        # Apply seasonal boost/penalty to get final score
        final_score = combined_score * seasonal_boost
        final_score = max(0.0, min(1.0, final_score))  # Clamp to 0-1

        # A match is "strong" if the final score is above threshold
        is_strong = final_score >= SIGNAL_MATCH_THRESHOLD

        if (
            combined_score >= SIGNAL_MATCH_THRESHOLD * 0.5
        ):  # Lower threshold for returning matches
            matches.append(
                {
                    "pattern_id": pattern["pattern_id"],
                    "site_id": pattern["site_id"],
                    "category": pattern["category"],
                    "description": pattern["description"],
                    "signal_similarity": round(signal_sim, 3),
                    "time_similarity": round(time_sim, 3),
                    "seasonal_boost": round(seasonal_boost, 2),
                    "combined_score": round(combined_score, 3),
                    "pattern_confidence": round(pattern["confidence"], 3),
                    "final_score": round(final_score, 3),
                    "auto_suppress": pattern["auto_suppress"],
                    "times_matched": pattern["times_matched"],
                    "is_strong_match": is_strong,
                    "season_tags": pattern.get("season_tags", []),
                    "mnf_tolerance_used": round(mnf_tolerance, 2),
                }
            )

    # Sort by final score descending
    matches.sort(key=lambda x: x["final_score"], reverse=True)

    return matches


def check_should_suppress(incident: Dict, site_id: str) -> Tuple[bool, Optional[Dict]]:
    """
    Check if an incident should be auto-suppressed based on matching patterns.

    Args:
        incident: Incident data dict
        site_id: Site ID

    Returns:
        Tuple of (should_suppress, matching_pattern or None)
    """
    matches = match_incident_to_patterns(incident, site_id)

    for match in matches:
        if match["is_strong_match"] and match["auto_suppress"]:
            # Update pattern match count
            update_pattern_match(match["pattern_id"])
            return True, match

    return False, None


def update_pattern_match(pattern_id: str) -> None:
    """Update pattern statistics when a match is found."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        df.loc[df["pattern_id"] == pattern_id, "times_matched"] += 1
        df.loc[df["pattern_id"] == pattern_id, "last_matched_at"] = (
            datetime.now().isoformat()
        )
        save_patterns_df(df)


def confirm_pattern_was_false(pattern_id: str) -> None:
    """User confirms that a suppressed/flagged incident was indeed a false alarm."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        df.loc[df["pattern_id"] == pattern_id, "times_confirmed_false"] += 1
        # Increase confidence
        current_conf = df.loc[df["pattern_id"] == pattern_id, "confidence"].values[0]
        df.loc[df["pattern_id"] == pattern_id, "confidence"] = min(
            1.0, current_conf + 0.05
        )
        df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = (
            datetime.now().isoformat()
        )
        save_patterns_df(df)


def report_pattern_was_real_leak(pattern_id: str) -> None:
    """User reports that a suppressed/flagged incident was actually a real leak."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        df.loc[df["pattern_id"] == pattern_id, "times_was_real_leak"] += 1
        # Decrease confidence significantly
        current_conf = df.loc[df["pattern_id"] == pattern_id, "confidence"].values[0]
        df.loc[df["pattern_id"] == pattern_id, "confidence"] = max(
            0.1, current_conf - 0.2
        )

        # If too many false negatives, deactivate pattern
        was_real = df.loc[df["pattern_id"] == pattern_id, "times_was_real_leak"].values[
            0
        ]
        was_false = df.loc[
            df["pattern_id"] == pattern_id, "times_confirmed_false"
        ].values[0]

        if was_real > 2 and was_real / (was_real + was_false) > 0.3:
            df.loc[df["pattern_id"] == pattern_id, "is_active"] = False
            log.warning(
                f"Deactivated pattern {pattern_id} due to high false negative rate"
            )

        df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = (
            datetime.now().isoformat()
        )
        save_patterns_df(df)


# ============================================
# PATTERN MANAGEMENT
# ============================================


def get_patterns_for_site(site_id: str) -> List[Dict]:
    """Get all patterns for a specific site."""
    df = get_patterns_df()
    site_patterns = df[(df["site_id"] == site_id) | (df["site_id"] == "ALL")]
    return site_patterns.to_dict("records")


def get_all_patterns() -> List[Dict]:
    """Get all patterns."""
    df = get_patterns_df()
    return df.to_dict("records")


def delete_pattern(pattern_id: str) -> bool:
    """Delete a pattern by ID."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        df = df[df["pattern_id"] != pattern_id]
        save_patterns_df(df)
        log.info(f"Deleted pattern {pattern_id}")
        return True

    return False


def toggle_pattern_active(pattern_id: str) -> bool:
    """Toggle a pattern's active status."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        current = df.loc[df["pattern_id"] == pattern_id, "is_active"].values[0]
        df.loc[df["pattern_id"] == pattern_id, "is_active"] = not current
        df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = (
            datetime.now().isoformat()
        )
        save_patterns_df(df)
        return True

    return False


def toggle_pattern_auto_suppress(pattern_id: str) -> bool:
    """Toggle a pattern's auto-suppress setting."""
    df = get_patterns_df()

    if pattern_id in df["pattern_id"].values:
        current = df.loc[df["pattern_id"] == pattern_id, "auto_suppress"].values[0]
        df.loc[df["pattern_id"] == pattern_id, "auto_suppress"] = not current
        df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = (
            datetime.now().isoformat()
        )
        save_patterns_df(df)
        return True

    return False


# ============================================
# UTILITY FUNCTIONS
# ============================================


def get_category_display_name(category: str) -> str:
    """Get human-readable category name."""
    category_names = {
        "false_alarm": "False Alarm",
        "pool_fill": "Pool Fill",
        "fire_test": "Fire System Test",
        "maintenance": "Planned Maintenance",
        "data_error": "Data Error / Sensor Issue",
        "temp_usage": "Known Temporary Usage",
        "irrigation": "Irrigation Schedule",
        "hvac": "HVAC System",
        "cleaning": "Cleaning Schedule",
        "event": "Scheduled Event",
        "other": "Other",
    }
    return category_names.get(category, category.replace("_", " ").title())


def get_pattern_summary(pattern: Dict) -> str:
    """Generate a human-readable summary of a pattern."""
    parts = []

    parts.append(
        f"Category: {get_category_display_name(pattern.get('category', 'unknown'))}"
    )

    recurrence = pattern.get("recurrence_rule", {})
    if recurrence.get("is_recurring"):
        rec_type = recurrence.get("type", "unknown")
        days = recurrence.get("days_of_week", [])
        if days:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_str = ", ".join([day_names[d] for d in days if d < 7])
            parts.append(f"Recurs: {rec_type} ({day_str})")
        else:
            parts.append(f"Recurs: {rec_type}")

    time_fp = pattern.get("time_fingerprint", {})
    if time_fp.get("time_window_start") and time_fp.get("time_window_end"):
        parts.append(
            f"Time: {time_fp['time_window_start']} - {time_fp['time_window_end']}"
        )

    parts.append(f"Confidence: {pattern.get('confidence', 0):.0%}")

    if pattern.get("auto_suppress"):
        parts.append("🚫 Auto-suppress ON")

    return " | ".join(parts)


# ============================================
# LOG PATTERN MATCHES
# ============================================


def log_pattern_match(
    incident_id: str,
    pattern_id: str,
    match_score: float,
    action_taken: str,  # "suppressed", "flagged", "ignored"
    site_id: str,
) -> None:
    """Log when a pattern match occurs for auditing."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "incident_id": incident_id,
        "pattern_id": pattern_id,
        "match_score": match_score,
        "action_taken": action_taken,
        "site_id": site_id,
    }

    if os.path.exists(PATTERN_MATCHES_LOG):
        df = pd.read_csv(PATTERN_MATCHES_LOG)
    else:
        df = pd.DataFrame(columns=list(log_entry.keys()))

    df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
    df.to_csv(PATTERN_MATCHES_LOG, index=False)


# ============================================
# CSV MIGRATION & SEASONAL UTILITIES
# ============================================


def migrate_csv_add_seasonal_columns() -> bool:
    """
    One-time migration: Add seasonal and MNF columns to existing CSV.
    Safe to run multiple times (idempotent).

    Returns:
        True if migration performed, False if already migrated
    """
    df = get_patterns_df()

    if df.empty:
        return False

    columns_to_add = {
        "season_tags": lambda: [[] for _ in range(len(df))],
        "baseline_term_usage_kL": lambda: [None] * len(df),
        "baseline_holiday_usage_kL": lambda: [None] * len(df),
        "mnf_tolerance_factor": lambda: [None] * len(df),
    }

    added = False
    for col, default_fn in columns_to_add.items():
        if col not in df.columns:
            df[col] = default_fn()
            log.info(f"Added column '{col}' to patterns CSV")
            added = True

    if added:
        save_patterns_df(df)
        log.info("CSV migration complete: added seasonal/MNF columns")
    else:
        log.debug("CSV already has seasonal/MNF columns; no migration needed")

    return added


def detect_pool_presence(
    site_id: str,
    usage_data: pd.DataFrame = None,
    summer_spike_threshold: float = 0.5,
) -> Tuple[bool, float]:
    """
    Auto-detect if school has pool based on summer usage spike.

    Args:
        site_id: Property ID
        usage_data: DataFrame with 'time' and 'usage_kL' columns
        summer_spike_threshold: % increase to indicate pool (default 50%)

    Returns:
        Tuple of (has_pool: bool, summer_increase_pct: float)
    """
    if usage_data is None or usage_data.empty:
        return False, 0.0

    # Ensure datetime column
    df = usage_data.copy()
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["month"] = df["time"].dt.month
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["month"] = df["timestamp"].dt.month
    else:
        return False, 0.0

    # Calculate average usage by season
    df["is_summer"] = df["month"].isin([12, 1, 2])

    # Find usage column
    usage_col = None
    for col in ["usage_kL", "usage", "consumption", "volume"]:
        if col in df.columns:
            usage_col = col
            break

    if not usage_col:
        return False, 0.0

    summer_usage = df[df["is_summer"]][usage_col].mean()
    term_usage = df[~df["is_summer"]][usage_col].mean()

    if pd.isna(summer_usage) or pd.isna(term_usage) or term_usage == 0:
        return False, 0.0

    increase_pct = (summer_usage - term_usage) / term_usage
    has_pool = increase_pct >= summer_spike_threshold

    return has_pool, round(increase_pct, 2)


def update_pattern_baseline_usage(
    pattern_id: str,
    term_usage_kL: float,
    holiday_usage_kL: float,
) -> bool:
    """
    Update baseline usage values for a pattern.

    Args:
        pattern_id: Pattern to update
        term_usage_kL: Average daily usage during term
        holiday_usage_kL: Average daily usage during holidays

    Returns:
        True if updated, False if pattern not found
    """
    df = get_patterns_df()

    if pattern_id not in df["pattern_id"].values:
        return False

    df.loc[df["pattern_id"] == pattern_id, "baseline_term_usage_kL"] = term_usage_kL
    df.loc[df["pattern_id"] == pattern_id, "baseline_holiday_usage_kL"] = holiday_usage_kL
    df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = datetime.now().isoformat()

    save_patterns_df(df)
    log.info(
        f"Updated pattern {pattern_id} baseline: "
        f"term={term_usage_kL} kL, holiday={holiday_usage_kL} kL"
    )
    return True


def update_pattern_season_tags(pattern_id: str, season_tags: List[str]) -> bool:
    """
    Update season tags for a pattern.

    Args:
        pattern_id: Pattern to update
        season_tags: List of season tags (e.g., ["summer", "term_1"])

    Returns:
        True if updated, False if pattern not found
    """
    # Validate season tags
    invalid_tags = [t for t in season_tags if t not in VALID_SEASON_TAGS]
    if invalid_tags:
        log.warning(f"Invalid season tags ignored: {invalid_tags}")
        season_tags = [t for t in season_tags if t in VALID_SEASON_TAGS]

    df = get_patterns_df()

    if pattern_id not in df["pattern_id"].values:
        return False

    df.loc[df["pattern_id"] == pattern_id, "season_tags"] = [season_tags]
    df.loc[df["pattern_id"] == pattern_id, "last_updated_at"] = datetime.now().isoformat()

    save_patterns_df(df)
    log.info(f"Updated pattern {pattern_id} season tags: {season_tags}")
    return True


# ============================================
# ADAPTIVE MNF TOLERANCE FUNCTIONS
# ============================================


def cv_to_tolerance(cv: float) -> float:
    """
    Map coefficient of variation to MNF tolerance factor.

    CV < 0.10: ±15% (stable site)
    CV < 0.20: ±25% (normal site)
    CV < 0.35: ±40% (variable site)
    CV >= 0.35: ±50% (noisy, capped)

    Args:
        cv: Coefficient of variation (std/mean)

    Returns:
        Tolerance factor (0.15 to 0.50)
    """
    for cv_threshold, tolerance in CV_TOLERANCE_MAP:
        if cv < cv_threshold:
            return tolerance

    # Fallback
    return MAX_MNF_TOLERANCE


def calculate_adaptive_mnf_tolerance(
    site_id: str,
    historical_data: pd.DataFrame = None,
    min_samples: int = MIN_MNF_SAMPLES,
    history_days: int = MNF_HISTORY_DAYS,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate site-specific MNF tolerance based on historical variation.

    Uses coefficient of variation (CV = std/mean) to determine appropriate
    tolerance range. Stable sites get tighter tolerance (±15%), variable
    sites get looser tolerance (up to ±50%).

    Args:
        site_id: Property ID
        historical_data: Optional DataFrame with MNF values
        min_samples: Minimum samples required (default 30)
        history_days: Days of history to consider (default 90)

    Returns:
        Tuple of (tolerance_factor, stats_dict)
        stats_dict contains: {cv, mean_mnf, std_mnf, sample_count, source}
    """
    stats = {
        "cv": None,
        "mean_mnf": None,
        "std_mnf": None,
        "sample_count": 0,
        "source": "default",
    }

    mnf_values = []

    # Strategy 1: Use provided historical data
    if historical_data is not None and not historical_data.empty:
        # Look for MNF columns
        mnf_cols = [c for c in historical_data.columns if "mnf" in c.lower()]
        if mnf_cols:
            for col in mnf_cols:
                values = historical_data[col].dropna().tolist()
                mnf_values.extend([v for v in values if v > 0])
            stats["source"] = "historical_data"

    # Strategy 2: Extract from existing patterns for this site
    if len(mnf_values) < min_samples:
        df = get_patterns_df()
        site_patterns = df[df["site_id"] == site_id]

        for _, pattern in site_patterns.iterrows():
            sig_fp = pattern.get("signal_fingerprint", {})
            if isinstance(sig_fp, str):
                try:
                    sig_fp = json.loads(sig_fp)
                except (json.JSONDecodeError, TypeError):
                    sig_fp = {}

            mnf_val = sig_fp.get("mnf_value_Lph")
            if mnf_val and float(mnf_val) > 0:
                mnf_values.append(float(mnf_val))

        if len(mnf_values) >= min_samples:
            stats["source"] = "pattern_history"

    # Check if we have enough samples
    stats["sample_count"] = len(mnf_values)

    if len(mnf_values) < min_samples:
        log.debug(
            f"Site {site_id}: insufficient MNF data ({len(mnf_values)} samples), "
            f"using default tolerance {DEFAULT_MNF_TOLERANCE}"
        )
        return DEFAULT_MNF_TOLERANCE, stats

    # Calculate coefficient of variation
    mnf_array = np.array(mnf_values)
    mean_mnf = np.mean(mnf_array)
    std_mnf = np.std(mnf_array)

    if mean_mnf <= 0:
        return DEFAULT_MNF_TOLERANCE, stats

    cv = std_mnf / mean_mnf

    stats["cv"] = round(cv, 4)
    stats["mean_mnf"] = round(mean_mnf, 2)
    stats["std_mnf"] = round(std_mnf, 2)

    # Map CV to tolerance
    tolerance = cv_to_tolerance(cv)

    log.info(
        f"Site {site_id}: CV={cv:.3f} → tolerance=±{tolerance:.0%} "
        f"(mean={mean_mnf:.1f}, std={std_mnf:.1f}, n={len(mnf_values)})"
    )

    return tolerance, stats


def calculate_mnf_similarity_adaptive(
    fp1: Dict,
    fp2: Dict,
    tolerance_factor: float = None,
) -> float:
    """
    Calculate MNF similarity using adaptive tolerance.

    Args:
        fp1: First fingerprint (pattern)
        fp2: Second fingerprint (incident)
        tolerance_factor: Override tolerance (uses DEFAULT_MNF_TOLERANCE if None)

    Returns:
        Similarity score (0.0 to 1.0)
    """
    # Extract MNF values
    mnf1_val = None
    mnf2_val = None

    # Try multiple field names for MNF
    for field in ["mnf_value_Lph", "mnf"]:
        if mnf1_val is None and fp1.get(field):
            try:
                mnf1_val = float(fp1[field])
            except (ValueError, TypeError):
                pass
        if mnf2_val is None and fp2.get(field):
            try:
                mnf2_val = float(fp2[field])
            except (ValueError, TypeError):
                pass

    # If no MNF data, return neutral score
    if not mnf1_val or not mnf2_val:
        return 0.5

    # Use provided tolerance or default
    if tolerance_factor is None:
        tolerance_factor = DEFAULT_MNF_TOLERANCE

    # Ensure tolerance is within bounds
    tolerance_factor = max(MIN_MNF_TOLERANCE, min(MAX_MNF_TOLERANCE, tolerance_factor))

    # Calculate adaptive range
    mnf1_lower = mnf1_val * (1 - tolerance_factor)
    mnf1_upper = mnf1_val * (1 + tolerance_factor)

    # Check if mnf2 falls within adaptive range
    if mnf1_lower <= mnf2_val <= mnf1_upper:
        # Within range - calculate how close to center
        center = mnf1_val
        distance = abs(mnf2_val - center)
        max_distance = mnf1_val * tolerance_factor
        # Score from 1.0 (at center) to 0.7 (at edge)
        return 1.0 - (0.3 * distance / max_distance) if max_distance > 0 else 1.0

    # Outside range - calculate partial credit based on how far outside
    if mnf2_val < mnf1_lower:
        overshoot = mnf1_lower - mnf2_val
        base = mnf1_val * tolerance_factor
        penalty = min(1.0, overshoot / base) if base > 0 else 1.0
        return max(0.0, 0.5 - (0.5 * penalty))
    else:
        overshoot = mnf2_val - mnf1_upper
        base = mnf1_val * tolerance_factor
        penalty = min(1.0, overshoot / base) if base > 0 else 1.0
        return max(0.0, 0.5 - (0.5 * penalty))


def recalculate_site_tolerances(site_ids: List[str] = None) -> Dict[str, float]:
    """
    Recalculate MNF tolerances for sites (quarterly maintenance).

    Args:
        site_ids: List of sites to update, or None for all

    Returns:
        Dict mapping site_id to new tolerance
    """
    df = get_patterns_df()

    if site_ids is None:
        site_ids = df["site_id"].unique().tolist()

    results = {}

    for site_id in site_ids:
        new_tolerance, stats = calculate_adaptive_mnf_tolerance(site_id)
        results[site_id] = new_tolerance

        # Update all patterns for this site
        site_mask = df["site_id"] == site_id
        if site_mask.any():
            old_tolerances = df.loc[site_mask, "mnf_tolerance_factor"].dropna().unique()
            df.loc[site_mask, "mnf_tolerance_factor"] = new_tolerance

            log.info(
                f"Site {site_id}: updated tolerance from {list(old_tolerances)} "
                f"to ±{new_tolerance:.0%}"
            )

    save_patterns_df(df)
    log.info(f"Recalculated MNF tolerances for {len(results)} sites")

    return results


def update_pattern_tolerance(pattern_id: str, tolerance: float = None) -> bool:
    """
    Update MNF tolerance for a specific pattern.

    Args:
        pattern_id: Pattern to update
        tolerance: New tolerance, or None to auto-calculate

    Returns:
        True if updated, False if pattern not found
    """
    df = get_patterns_df()

    if pattern_id not in df["pattern_id"].values:
        return False

    idx = df[df["pattern_id"] == pattern_id].index[0]
    site_id = df.loc[idx, "site_id"]

    if tolerance is None:
        tolerance, _ = calculate_adaptive_mnf_tolerance(site_id)

    df.loc[idx, "mnf_tolerance_factor"] = tolerance
    df.loc[idx, "last_updated_at"] = datetime.now().isoformat()

    save_patterns_df(df)
    log.info(f"Pattern {pattern_id}: tolerance updated to ±{tolerance:.0%}")

    return True


# ============================================
# PATTERN STALENESS CLEANUP
# ============================================


def cleanup_stale_patterns(
    inactivity_threshold_days: int = STALENESS_THRESHOLD_DAYS,
    decay_period_days: int = CONFIDENCE_DECAY_PERIOD_DAYS,
) -> Dict[str, int]:
    """
    Auto-deactivate and decay confidence of stale patterns.

    Runs daily at 2 AM via scheduler (or manually via trigger_staleness_cleanup_now).
    - Patterns inactive for 120+ days: auto-deactivated
    - Patterns inactive for 30+ days: confidence decays 5% per 30-day period
    - Confidence floor at 10%

    Args:
        inactivity_threshold_days: Days before auto-deactivation (default 120)
        decay_period_days: Period for confidence decay (default 30)

    Returns:
        Dict with counts: {deactivated: N, decayed: N, unchanged: N}
    """
    df = get_patterns_df()
    now = datetime.now()

    stats = {"deactivated": 0, "decayed": 0, "unchanged": 0}

    if df.empty:
        return stats

    for idx, pattern in df.iterrows():
        # Skip already inactive patterns
        if not pattern.get("is_active", True):
            continue

        # Determine last activity timestamp
        last_matched = pd.to_datetime(pattern.get("last_matched_at"), errors="coerce")
        last_updated = pd.to_datetime(pattern.get("last_updated_at"), errors="coerce")
        created_at = pd.to_datetime(pattern.get("created_at"), errors="coerce")

        # Use most recent valid timestamp
        timestamps = [t for t in [last_matched, last_updated, created_at] if pd.notna(t)]
        if not timestamps:
            continue
        last_activity = max(timestamps)

        days_inactive = (now - last_activity).days

        if days_inactive >= inactivity_threshold_days:
            # Auto-deactivate
            df.loc[idx, "is_active"] = False
            df.loc[idx, "notes"] = (
                f"Auto-deactivated after {days_inactive} days inactive "
                f"({now.strftime('%Y-%m-%d')})"
            )
            df.loc[idx, "last_updated_at"] = now.isoformat()
            log.info(
                f"Deactivated stale pattern {pattern['pattern_id']} "
                f"({days_inactive} days inactive)"
            )
            stats["deactivated"] += 1

        elif days_inactive >= decay_period_days:
            # Apply confidence decay
            periods = days_inactive // decay_period_days
            decay_factor = CONFIDENCE_DECAY_RATE ** periods
            old_conf = float(pattern.get("confidence", 0.5))
            new_conf = max(CONFIDENCE_FLOOR, old_conf * decay_factor)

            if abs(old_conf - new_conf) > 0.01:  # Only update if meaningful change
                df.loc[idx, "confidence"] = round(new_conf, 3)
                df.loc[idx, "last_updated_at"] = now.isoformat()
                log.debug(
                    f"Pattern {pattern['pattern_id']} confidence decayed: "
                    f"{old_conf:.2f} -> {new_conf:.2f}"
                )
                stats["decayed"] += 1
            else:
                stats["unchanged"] += 1
        else:
            stats["unchanged"] += 1

    if stats["deactivated"] > 0 or stats["decayed"] > 0:
        save_patterns_df(df)
        log.info(
            f"Staleness cleanup complete: {stats['deactivated']} deactivated, "
            f"{stats['decayed']} decayed, {stats['unchanged']} unchanged"
        )

    return stats


def reactivate_stale_pattern(
    pattern_id: str,
    confidence_reset: float = REACTIVATION_CONFIDENCE,
) -> bool:
    """
    Reactivate a deactivated pattern when similar incident matches.

    Called automatically when record_pattern() finds a deactivated pattern
    with high similarity to the new incident.

    Args:
        pattern_id: ID of pattern to reactivate
        confidence_reset: Confidence to reset to (default 50%)

    Returns:
        True if reactivated, False if pattern not found
    """
    df = get_patterns_df()

    if pattern_id not in df["pattern_id"].values:
        log.warning(f"Cannot reactivate: pattern {pattern_id} not found")
        return False

    idx = df[df["pattern_id"] == pattern_id].index[0]
    was_active = df.loc[idx, "is_active"]

    df.loc[idx, "is_active"] = True
    df.loc[idx, "confidence"] = confidence_reset
    df.loc[idx, "last_updated_at"] = datetime.now().isoformat()
    df.loc[idx, "notes"] = (
        f"Reactivated with {confidence_reset:.0%} confidence "
        f"({datetime.now().strftime('%Y-%m-%d')})"
    )

    save_patterns_df(df)

    if not was_active:
        log.info(
            f"Reactivated pattern {pattern_id} with {confidence_reset:.0%} confidence"
        )

    return True


def trigger_staleness_cleanup_now() -> Dict[str, int]:
    """
    Manually trigger staleness cleanup (for admin/testing).

    Returns:
        Stats dict from cleanup_stale_patterns()
    """
    log.info("Manual staleness cleanup triggered")
    return cleanup_stale_patterns()


# %%
