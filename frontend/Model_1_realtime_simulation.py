# Updated Model_1.py with modifications for up_to_date

# %%
import pandas as pd
import numpy as np
from datetime import timedelta, datetime, time
import logging
import os
import yaml
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from concurrent.futures import ProcessPoolExecutor  # Added for parallel processing

# Modularized utilities (Phase 2 extraction)
from statistical_utils import (
    robust_median as _robust_median,
    robust_mad as _robust_mad,
    detect_cusum as _detect_cusum,
)
from leak_scoring import (
    get_severity as _get_severity,
    get_confidence as _get_confidence,
    get_persistence_needed as _get_persistence_needed,
    categorize_leak as _categorize_leak,
)
from incident_serialization import (
    canonize_incident as _canonize_incident,
    canonize_confirmed_df as _canonize_confirmed_df,
    to_dashboard_dict as _to_dashboard_dict,
)
from leak_event_charts import (
    create_confidence_evolution_mini as _create_confidence_mini,
    to_plotly_figs as _to_plotly_figs,
    _create_anomaly_timeline,
    _create_mnf_control_chart,
    _create_after_hours_breakdown,
    _create_enhanced_heatmap,
    plot_leak_event_matplotlib as _plot_leak_event,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("leak_detection.log"), logging.StreamHandler()],
)


class SchoolLeakDetector:
    def __init__(self, df, site_id, cfg, leak_log=None, up_to_date=None):
        self.df = df.copy()
        self.site_id = site_id
        self.cfg = cfg
        self.leak_log = leak_log if leak_log else []
        self.incidents = []
        self.excluded_dates = set()
        self.daily = None
        self.pattern_suppressions = {}
        self.theta_min = None  # adaptive threshold (MNF baseline)
        self.up_to_date = pd.to_datetime(up_to_date) if up_to_date else None
        # ✅ FIX: Store signal components by date to enable consistent confidence calculation
        # Even when rolling baselines change, we use the originally calculated signals
        self.signal_components_by_date = {}  # {date: {sub_scores, deltaNF, NF_MAD}}
        # ✅ FIX: Store FROZEN confidence values to prevent recalculation
        # Once a confidence is calculated for a date, it NEVER changes
        self.confidence_by_date = {}  # {date_key: confidence_value}
        # Cache for rolling baseline calculations
        # Key: (date_str, metric_name), Value: (median, mad)
        self._baseline_cache = {}
        # Cache for hourly profile calculations
        self._hourly_profile_cache = {}

    def preprocess(self):
        # Ensure timezone-naive timestamps and hourly alignment
        self.df["time"] = pd.to_datetime(self.df["time"]).dt.tz_localize(None)
        if self.up_to_date:
            self.df = self.df[self.df["time"] <= self.up_to_date]
        self.df.set_index("time", inplace=True)
        self.df = self.df.resample("h").sum()
        self.df.interpolate(method="linear", limit=3, inplace=True)
        self.df["flow"].fillna(0, inplace=True)
        self.df["flow"] = self.df["flow"].clip(lower=0)
        self.df["date"] = self.df.index.date
        self.df["hour"] = self.df.index.hour
        q99_9 = self.df["flow"].quantile(0.999)
        self.df["outlier"] = self.df["flow"] > q99_9
        logging.info(f"{self.site_id}: Preprocessed {len(self.df)} hourly records")

    def robust_median(self, series):
        return _robust_median(series)

    def robust_mad(self, series):
        return _robust_mad(series)

    def detect_cusum(self, series, k, h, mad):
        return _detect_cusum(series, k, h, mad)

    def get_rolling_baseline(self, d, metric, daily_series):
        d = pd.to_datetime(d).date()
        hist_start = d - timedelta(days=self.cfg["baseline_window_days"])
        sub = daily_series[
            (daily_series.index.date >= hist_start) & (daily_series.index.date < d)
        ]
        sub = sub[~sub.index.isin([pd.Timestamp(date) for date in self.excluded_dates])]
        return self.robust_median(sub), self.robust_mad(sub)

    def get_hourly_profile(self, h, d):
        d = pd.to_datetime(d).date()
        hist_start = d - timedelta(days=self.cfg["baseline_window_days"])
        mask = (
            (self.df["date"] >= hist_start)
            & (self.df["date"] < d)
            & (self.df["hour"] == h)
        )
        sub = self.df[mask]["flow"]
        sub = sub[
            ~pd.Series(self.df[mask].index.date, index=self.df[mask].index).isin(
                self.excluded_dates
            )
        ]
        return self.robust_median(sub), self.robust_mad(sub)

    def baselining(self):
        night_mask = (self.df["hour"] >= self.cfg["night_start"]) & (
            self.df["hour"] < self.cfg["night_end"]
        )
        self.daily = pd.DataFrame(index=pd.to_datetime(np.unique(self.df["date"])))
        self.daily["NF_d"] = (
            self.df[night_mask]
            .groupby("date")["flow"]
            .apply(lambda x: np.percentile(x, 10))
        )

        # ✅ Correct after-hours: hour >= after_hours_start OR hour < after_hours_end
        ah_mask = (self.df["hour"] >= self.cfg["after_hours_start"]) | (
            self.df["hour"] < self.cfg["after_hours_end"]
        )
        self.daily["A_d"] = (
            self.df[ah_mask].groupby("date")["flow"].sum() / 1000.0
        )  # kL

        logging.info(f"{self.site_id}: Baselined {len(self.daily)} days")

    def signals_and_score(self, d):
        d_dt = pd.to_datetime(d)
        NF_d = self.daily.loc[d, "NF_d"]
        NF_base, NF_MAD = self.get_rolling_baseline(d, "NF_d", self.daily["NF_d"])
        deltaNF = max(0, NF_d - NF_base)
        thresh = max(3 * NF_MAD, self.cfg["abs_floor_lph"])
        s_MNF = (
            max(0, min(1, (deltaNF - thresh) / (thresh + self.cfg["abs_floor_lph"])))
            if deltaNF > thresh
            else 0
        )

        # Vectorized residual calculation
        d_date = d_dt.date()
        after_hours_data = self.df[
            (self.df["date"] == d_date)
            & (
                (self.df["hour"] >= self.cfg["after_hours_start"])
                | (self.df["hour"] < self.cfg["after_hours_end"])
            )
        ]
        residuals = []
        mad_rs = []
        if not after_hours_data.empty:
            hourly_profiles = [
                self.get_hourly_profile(h, d) for h in after_hours_data["hour"]
            ]
            residuals = after_hours_data["flow"] - pd.Series(
                [p[0] for p in hourly_profiles], index=after_hours_data.index
            )
            mad_rs = [p[1] for p in hourly_profiles]
        after_hours_count = len(residuals)
        s_RES = 0
        if after_hours_count > 0:
            med_res = np.median(residuals)
            med_mad_r = np.median(mad_rs)
            pos_frac = sum(r > 0 for r in residuals) / after_hours_count
            thresh_r = max(3 * med_mad_r, self.cfg["abs_floor_lph"])
            s_RES = (
                1
                if pos_frac >= 0.7 and med_res > thresh_r
                else max(0, min(1, med_res / (2 * thresh_r)))
            )

        hist_NF = self.daily["NF_d"][:d]
        mad_nf_hist = self.robust_mad(hist_NF)
        cusum_NF = self.detect_cusum(
            hist_NF.values, self.cfg["cusum_k"], self.cfg["cusum_h"], mad_nf_hist
        )
        hist_A = self.daily["A_d"][:d]
        mad_a_hist = self.robust_mad(hist_A)
        cusum_A = self.detect_cusum(
            hist_A.values, self.cfg["cusum_k"], self.cfg["cusum_h"], mad_a_hist
        )
        s_CUSUM = max(cusum_NF, cusum_A)

        A_d = self.daily.loc[d, "A_d"]
        A_base, A_MAD = self.get_rolling_baseline(d, "A_d", self.daily["A_d"])
        deltaA = A_d - A_base
        threshA = max(3 * A_MAD, self.cfg["sustained_after_hours_delta_kl"])
        prev_d = d - timedelta(days=1)
        s_AH = 0
        if prev_d in self.daily.index:
            prev_deltaA = (
                self.daily.loc[prev_d, "A_d"]
                - self.get_rolling_baseline(prev_d, "A_d", self.daily["A_d"])[0]
            )
            sustained = deltaA > threshA and prev_deltaA > threshA
            s_AH = 1 if sustained else max(0, min(1, deltaA / (2 * threshA)))

        s_BF = 0
        daily_data = self.df[(self.df["date"] == d_date)]
        if not daily_data.empty:
            hourly_profiles = [
                self.get_hourly_profile(h, d)[0] for h in daily_data["hour"]
            ]
            spikes = (
                daily_data["flow"]
                > pd.Series(hourly_profiles, index=daily_data.index)
                * self.cfg["spike_multiplier"]
            )
            if spikes.any():
                next_d = d + timedelta(days=1)
                if next_d in self.daily.index:
                    next_deltaNF = (
                        self.daily.loc[next_d, "NF_d"]
                        - self.get_rolling_baseline(next_d, "NF_d", self.daily["NF_d"])[
                            0
                        ]
                    )
                    if next_deltaNF > max(
                        3
                        * self.get_rolling_baseline(next_d, "NF_d", self.daily["NF_d"])[
                            1
                        ],
                        self.cfg["abs_floor_lph"],
                    ):
                        s_BF = 1

        sub_scores = {
            "MNF": s_MNF,
            "RESIDUAL": s_RES,
            "CUSUM": s_CUSUM,
            "AFTERHRS": s_AH,
            "BURSTBF": s_BF,
        }
        leak_score = (
            sum(self.cfg["score_weights"][k] * v for k, v in sub_scores.items()) * 100
        )
        leak_score = min(100, max(0, leak_score))

        return sub_scores, leak_score, deltaNF, NF_MAD

    def diagnose_burstbf(self, d):
        """Diagnostic method to check BURST/BF signal calculation for a specific date"""
        d_date = d.date() if hasattr(d, "date") else d

        # Get the daily data for this date
        daily_data = self.df[(self.df["date"] == d_date)]

        if daily_data.empty:
            return {
                "error": "No data found for this date",
                "date": str(d_date),
            }

        # Check for spikes
        hourly_profiles = []
        spike_thresholds = []
        actual_flows = []
        spikes_detected = []

        for idx, row in daily_data.iterrows():
            h = row["hour"]
            profile_val, _ = self.get_hourly_profile(h, d)
            threshold = profile_val * self.cfg["spike_multiplier"]
            is_spike = row["flow"] > threshold

            hourly_profiles.append(profile_val)
            spike_thresholds.append(threshold)
            actual_flows.append(row["flow"])
            spikes_detected.append(is_spike)

        has_spikes = any(spikes_detected)

        # Check next day's NF increase if spikes detected
        next_day_check = None
        s_BF_value = 0

        if has_spikes:
            next_d = d + timedelta(days=1)
            if next_d in self.daily.index:
                baseline_nf, mad_nf = self.get_rolling_baseline(
                    next_d, "NF_d", self.daily["NF_d"]
                )
                next_nf = self.daily.loc[next_d, "NF_d"]
                next_deltaNF = next_nf - baseline_nf
                required_threshold = max(3 * mad_nf, self.cfg["abs_floor_lph"])

                next_day_check = {
                    "next_date": str(next_d.date()),
                    "next_day_NF": float(next_nf),
                    "baseline_NF": float(baseline_nf),
                    "delta_NF": float(next_deltaNF),
                    "MAD": float(mad_nf),
                    "required_threshold": float(required_threshold),
                    "threshold_met": next_deltaNF > required_threshold,
                }

                if next_deltaNF > required_threshold:
                    s_BF_value = 1
            else:
                next_day_check = {"error": "Next day not in data"}

        return {
            "date": str(d_date),
            "has_spikes_detected": has_spikes,
            "spike_count": sum(spikes_detected),
            "spike_multiplier_config": self.cfg["spike_multiplier"],
            "hourly_details": [
                {
                    "hour": int(daily_data.iloc[i]["hour"]),
                    "actual_flow": float(actual_flows[i]),
                    "hourly_profile": float(hourly_profiles[i]),
                    "spike_threshold": float(spike_thresholds[i]),
                    "is_spike": bool(spikes_detected[i]),
                    "exceeds_by": float(actual_flows[i] - spike_thresholds[i]),
                }
                for i in range(len(actual_flows))
            ],
            "next_day_check": next_day_check,
            "final_BURSTBF_score": s_BF_value,
        }

    def get_severity(self, deltaNF):
        return _get_severity(deltaNF, self.cfg["severity_bands_lph"])

    def to_dashboard_dict(self, incident):
        """Return incident dict with serializable types for dashboard UI"""
        return {
            "site_id": incident["site_id"],
            "status": incident.get("status", ""),
            "start_day": pd.to_datetime(incident["start_day"]),
            "last_day": pd.to_datetime(incident["last_day"]),
            "severity_max": incident.get("severity_max", "S1"),
            "confidence": float(incident.get("confidence", 0)),
            "volume_lost_kL": float(incident.get("volume_lost_kL", 0)),
            "reason_codes": list(incident.get("reason_codes", [])),
            "alert_date": pd.to_datetime(
                incident.get("alert_date", incident["last_day"])
            ),
        }

    def get_confidence(self, sub_scores, persistence_days, deltaNF, NF_MAD):
        return _get_confidence(sub_scores, persistence_days, deltaNF, NF_MAD)

    def create_confidence_evolution_mini(self, incident):
        """Create mini bar chart showing confidence building over duration period"""
        return _create_confidence_mini(self, incident)

    def get_persistence_needed(self, deltaNF, sig_agree, confidence):
        return _get_persistence_needed(
            deltaNF, sig_agree, confidence, self.cfg["persistence_gates"]
        )

    def get_adaptive_threshold(self):
        night_mask = (self.df["hour"] >= self.cfg["night_start"]) & (
            self.df["hour"] < self.cfg["night_end"]
        )
        mnf = (
            self.df[night_mask]
            .groupby("date")["flow"]
            .apply(lambda x: np.percentile(x, 10))
        )
        self.theta_min = max(
            self.cfg["abs_floor_lph"],
            self.robust_median(mnf) + 2 * self.robust_mad(mnf),
        )

        logging.info(f"{self.site_id}: Adaptive theta_min = {self.theta_min} L/h")
        return {"theta_min": self.theta_min}

    def categorize_leak(self, incident):
        # Use site-specific MNF baseline for scaling
        baseline = self.theta_min if self.theta_min else self.cfg["abs_floor_lph"]
        event_df = self.df[
            (self.df["date"] >= incident["start_day"].date())
            & (self.df["date"] <= incident["last_day"].date())
        ]
        avg_flow = event_df["flow"].mean()
        std_dev = event_df["flow"].std()
        return _categorize_leak(avg_flow, std_dev, baseline)

    def plot_leak_event(self, incident, site_cfg):
        """Enhanced leak event plot (delegated to leak_event_charts module)"""
        return _plot_leak_event(self, incident, site_cfg)

    def state_machine(self):

        if (
            self.daily is None
            or not isinstance(self.daily, pd.DataFrame)
            or self.daily.empty
        ):
            self.baselining()
        days = sorted(self.daily.index)
        if not days:
            return {}

        # Configs
        site_cfg = self.get_adaptive_threshold()
        merge_gap_days = int(self.cfg.get("merge_gap_days", 2))

        # Helpers
        def sev_rank(s):
            try:
                return int(str(s).lstrip("S"))
            except Exception:
                return 1

        daily_outputs = {}
        active = None
        last_committed = None  # last item in self.incidents

        for i, d in enumerate(days):
            # Wait until we have enough baseline history
            if (d - days[0]).days < self.cfg["baseline_window_days"]:
                daily_outputs[d] = {"status": "OK", "next_action": "None"}
                continue

            # ✅ FIX: Check if we already have signal components for this date
            # If yes, use the stored values to prevent recalculation from changed baselines
            d_key = d.strftime("%Y-%m-%d")
            if d_key in self.signal_components_by_date:
                # Use previously calculated signals
                cached = self.signal_components_by_date[d_key]
                sub_scores = cached["sub_scores"]
                leak_score = cached["leak_score"]
                deltaNF = cached["deltaNF"]
                NF_MAD = cached["NF_MAD"]
                logging.debug(
                    f"[{self.site_id}] {d_key}: Using CACHED signals - deltaNF={deltaNF:.1f}"
                )
            else:
                # Calculate fresh and store
                sub_scores, leak_score, deltaNF, NF_MAD = self.signals_and_score(d)
                self.signal_components_by_date[d_key] = {
                    "sub_scores": sub_scores.copy(),
                    "leak_score": leak_score,
                    "deltaNF": deltaNF,
                    "NF_MAD": NF_MAD,
                }
                logging.debug(
                    f"[{self.site_id}] {d_key}: CALCULATED FRESH signals - deltaNF={deltaNF:.1f}"
                )

            severity = self.get_severity(deltaNF)
            signals_fired = [k for k, v in sub_scores.items() if v > 0]

            # Pattern suppression (episodic fills)
            suppress = False
            if "BURSTBF" in signals_fired and sub_scores["BURSTBF"] > 0:
                nd = d + timedelta(days=1)
                if nd in self.daily.index:
                    nd_base, nd_mad = self.get_rolling_baseline(
                        nd, "NF_d", self.daily["NF_d"]
                    )
                    nd_delta = self.daily.loc[nd, "NF_d"] - nd_base
                    if nd_delta <= site_cfg["theta_min"]:
                        suppress = True
                        self.pattern_suppressions[d] = "EPISODIC FILL"

            if suppress:
                daily_outputs[d] = {
                    "status": "OK",
                    "next_action": "None",
                    "suppressed": self.pattern_suppressions[d],
                }
                continue

            # Confidence & persistence projection
            persistence_days = 1 if active is None else active["days_persisted"] + 1

            # ✅ FIX: Use FROZEN confidence from detector cache if available
            # The detector cache is pre-populated with frozen values from previous runs
            if d_key in self.confidence_by_date:
                confidence = self.confidence_by_date[d_key]
                logging.info(
                    f"[{self.site_id}] {d_key}: Using FROZEN confidence={confidence:.1f}%"
                )
            else:
                # Calculate fresh and freeze it
                confidence = self.get_confidence(
                    sub_scores, persistence_days, deltaNF, NF_MAD
                )
                self.confidence_by_date[d_key] = confidence
                logging.info(
                    f"[{self.site_id}] {d_key}: CALCULATED NEW confidence={confidence:.1f}% (now frozen)"
                )

            # Trigger condition
            trigger = (leak_score >= 30) or (
                sev_rank(severity) > 1 and deltaNF > site_cfg["theta_min"]
            )

            if trigger:
                if active:

                    # contiguous day → extend
                    if (d - active["last_day"]).days == 1:
                        active["last_day"] = d
                        active["days_persisted"] += 1

                    # small gap → merge into active
                    elif 1 < (d - active["last_day"]).days <= merge_gap_days:
                        gap = (
                            d - active["last_day"]
                        ).days - 1  # days with no data but within merge window
                        active["days_persisted"] += 1 + max(0, gap)
                        active["last_day"] = d

                    else:
                        # Try merging with the last committed incident if within gap
                        if (
                            last_committed
                            and 0
                            < (d - last_committed["last_day"]).days
                            <= merge_gap_days
                        ):
                            gap = (d - last_committed["last_day"]).days - 1
                            active = last_committed
                            active["days_persisted"] += 1 + max(0, gap)
                            active["last_day"] = d
                        else:
                            # start fresh
                            active = {
                                "site_id": self.site_id,
                                "status": "WATCH",
                                "start_day": d,
                                "last_day": d,
                                "max_deltaNF": 0.0,
                                "severity_max": "S1",
                                "days_persisted": 1,
                                "reason_codes": set(),
                                "volume_lost_kL": 0.0,
                                "confidence": 0.0,
                                # ✅ FIX: Store signal components by date for consistent confidence recalculation
                                "signal_components_by_date": {},
                            }
                            self.incidents.append(active)
                            last_committed = active

                    # Update attributes
                    active["max_deltaNF"] = max(active["max_deltaNF"], float(deltaNF))
                    if sev_rank(severity) > sev_rank(active["severity_max"]):
                        active["severity_max"] = severity
                    active["reason_codes"] |= set(signals_fired)
                    active["volume_lost_kL"] += float(deltaNF) * 24 / 1000.0

                    # ✅ FIX: Store signal components for this date in the incident
                    # This allows us to recalculate confidence with correct persistence later
                    if "signal_components_by_date" not in active:
                        active["signal_components_by_date"] = {}
                    active["signal_components_by_date"][d_key] = {
                        "sub_scores": sub_scores.copy(),
                        "deltaNF": float(deltaNF),
                        "NF_MAD": float(NF_MAD),
                        "confidence": float(
                            confidence
                        ),  # Store frozen confidence value
                    }

                    # Update main confidence to always be the LATEST day's value
                    active["confidence"] = float(confidence)

                    logging.info(
                        f"[{self.site_id}] Incident {active['start_day'].date()} -> {d_key}: "
                        f"persist={persistence_days}, conf={confidence:.1f}%, deltaNF={deltaNF:.1f}, "
                        f"NF_MAD={NF_MAD:.1f}, sub_scores={sub_scores}, "
                        f"signal_comp_count={len(active['signal_components_by_date'])}"
                    )

                    # (Re)compute persistence gate and alert_date EVERY day
                    needed = self.get_persistence_needed(
                        active["max_deltaNF"],
                        len(active["reason_codes"]),
                        active["confidence"],
                    )
                    active["alert_date"] = pd.to_datetime(
                        active["start_day"]
                    ) + timedelta(days=needed - 1)

                    # Escalation
                    if active["days_persisted"] >= needed:
                        if sev_rank(active["severity_max"]) <= 3:
                            active["status"] = "INVESTIGATE"
                        if sev_rank(active["severity_max"]) >= 4 or (
                            sev_rank(active["severity_max"]) >= 2
                            and active["confidence"] >= 70
                        ):
                            active["status"] = "CALL"

                else:
                    # Start first incident
                    active = {
                        "site_id": self.site_id,
                        "status": "WATCH",
                        "start_day": d,
                        "last_day": d,
                        "max_deltaNF": float(deltaNF),
                        "severity_max": severity,
                        "days_persisted": 1,
                        "reason_codes": set(signals_fired),
                        "volume_lost_kL": float(deltaNF) * 24 / 1000.0,
                        "confidence": float(confidence),
                        # ✅ FIX: Store signal components by date for consistent confidence recalculation
                        "signal_components_by_date": {
                            d_key: {
                                "sub_scores": sub_scores.copy(),
                                "deltaNF": float(deltaNF),
                                "NF_MAD": float(NF_MAD),
                                "confidence": float(
                                    confidence
                                ),  # Store frozen confidence value
                            }
                        },
                    }
                    needed = self.get_persistence_needed(
                        deltaNF, len(signals_fired), confidence
                    )
                    active["alert_date"] = pd.to_datetime(d) + timedelta(
                        days=needed - 1
                    )
                    self.incidents.append(active)
                    last_committed = active

                # Closure (night-flow based) — but skip for confirmed incidents
                if active and (active["status"] not in ("INVESTIGATE", "CALL")):
                    close_thresh = max(3 * NF_MAD, site_cfg["theta_min"])
                    if deltaNF <= close_thresh:
                        active["close_reason"] = "self-resolved/benign"
                        active = None

            else:
                # No trigger today ⇒ close only non-confirmed actives
                if active and (active["status"] not in ("INVESTIGATE", "CALL")):
                    active["close_reason"] = "self-resolved/benign"
                    active = None

            # Daily UI record
            status = active["status"] if active else "OK"
            daily_outputs[d] = {
                "status": status,
                "severity": (active["severity_max"] if active else None),
                "confidence": float(confidence),
                "deltaNF": float(deltaNF),
                "days_persisted": (active["days_persisted"] if active else 0),
                "est_volume_lost_kL": (active["volume_lost_kL"] if active else 0.0),
                "reason_codes": (
                    ", ".join(sorted(active["reason_codes"])) if active else ""
                ),
                "next_action": (
                    "Monitor next night"
                    if status == "WATCH"
                    else (
                        "Caretaker walk-through"
                        if status == "INVESTIGATE"
                        else "Escalate to plumber" if status == "CALL" else "None"
                    )
                ),
            }

        # Persist for reuse (avoid recompute)
        self.daily_outputs = daily_outputs

        # ✅ DEBUG: Log final incident state
        for inc in self.incidents:
            inc_id = inc.get(
                "event_id", f"{inc.get('start_day')}_{inc.get('last_day')}"
            )
            has_sig = "signal_components_by_date" in inc
            sig_count = len(inc.get("signal_components_by_date", {}))
            logging.info(
                f"[STATE_MACHINE_END] {self.site_id} - {inc_id}: "
                f"has_signal_components={has_sig}, count={sig_count}"
            )

        return daily_outputs

    def to_plotly_figs(self, incident, window_days=30):
        """Generate enhanced professional charts (delegated to leak_event_charts module)"""
        return _to_plotly_figs(self, incident, window_days)


def load_tafe_data(file_path: str) -> dict:
    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
    except FileNotFoundError:
        logging.error(f"Data file not found at: {file_path}")
        raise

    all_dfs = []
    for sheet in sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet)
            df.columns = df.columns.str.strip()
            required_cols = [
                "Timestamp",
                "De-identified Property Name",
                "Sum of Usage (L)",
            ]
            if not set(required_cols).issubset(df.columns):
                continue
            df = df.dropna(subset=["Timestamp", "De-identified Property Name"])
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df = df.dropna(subset=["Timestamp"])
            df = df.rename(
                columns={
                    "De-identified Property Name": "site_id",
                    "Timestamp": "time",
                    "Sum of Usage (L)": "flow",
                }
            )
            df["flow"] = pd.to_numeric(df["flow"], errors="coerce").fillna(0)
            df["flow"] = df["flow"].clip(lower=0)
            all_dfs.append(df)
        except Exception as e:
            logging.error(f"Error processing sheet {sheet}: {e}")
            continue

    combined_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(
        subset=["time", "site_id"]
    )
    school_dfs = {
        school: group[["time", "flow"]].sort_values("time").reset_index(drop=True)
        for school, group in combined_df.groupby("site_id")
    }
    logging.info(f"Successfully loaded and split data for {len(school_dfs)} sites.")
    return school_dfs


def check_data_frequency(df, site_id):
    time_diffs = df["time"].diff().dropna()
    median_freq = time_diffs.median()
    if median_freq > timedelta(hours=2):
        logging.error(
            f"{site_id}: Data frequency too irregular (median {median_freq}). Cannot proceed."
        )
        raise ValueError(f"Data frequency too irregular for {site_id}")
    elif median_freq > timedelta(hours=1.5):
        logging.warning(
            f"{site_id}: Data frequency irregular (median {median_freq}). Results may be unreliable."
        )
    else:
        logging.info(f"{site_id}: Data frequency OK (median {median_freq})")


def process_site(args):
    """
    Engine-side single-site runner used by the replay loop.

    Expects args like: (site_id, df_slice, cfg, [...optional...], up_to_date, prev_signal_components, prev_confidence_by_date)
    Returns: (site_id, detector, confirmed_df)

    Responsibilities:
      - Defensive normalization of df_slice (time dtype, sort, basic checks)
      - Instantiate SchoolLeakDetector and run preprocess/state_machine
      - Canonicalize incident schemas (start_time/end_time/event_id/alert_date)
      - Build a 'confirmed_df' table that downstream UI can consume
    """
    import logging
    import pandas as pd
    import numpy as np

    logger = globals().get("log", logging.getLogger("replay"))

    # -----------------------
    # Unpack & basic hygiene
    # -----------------------
    try:
        site_id, df_slice, cfg, *rest = args
    except Exception:
        logger.exception("process_site: invalid args shape: %r", args)
        return None, None, pd.DataFrame()

    # up_to_date is expected as the last positional item (if provided)
    # prev_signal_components and prev_confidence_by_date are the last two dict items
    up_to_date = None
    prev_signal_components = {}
    prev_confidence_by_date = {}

    if rest:
        # Look for dicts at the end (frozen confidence and signal components)
        for candidate in reversed(rest):
            if isinstance(candidate, dict) and any(
                k.startswith("202") for k in candidate.keys() if isinstance(k, str)
            ):
                # This looks like a date-keyed dict
                if not prev_confidence_by_date and all(
                    isinstance(v, (int, float)) for v in candidate.values()
                ):
                    prev_confidence_by_date = candidate
                elif not prev_signal_components:
                    prev_signal_components = candidate

        # Look for datetime (up_to_date)
        for candidate in reversed(rest):
            try:
                up_to_date = pd.to_datetime(candidate)
                break
            except Exception:
                continue

    # Defensive copy & column checks
    if df_slice is None or len(df_slice) == 0:
        logger.warning("%s: empty df_slice provided to process_site", site_id)
        return site_id, None, pd.DataFrame()

    df = df_slice.copy()

    # Ensure 'time' is present and is datetime
    if "time" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={"index": "time"})

    if "time" not in df.columns:
        logger.error("%s: df_slice missing 'time' column", site_id)
        return site_id, None, pd.DataFrame()

    # Safe datetime conversion (no chained assignment)
    df.loc[:, "time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time")

    # Optional: quick data frequency check for logging observability
    try:
        med_step = df["time"].diff().median()
        logger.info("%s: Data frequency OK (median %s)", site_id, med_step)
    except Exception:
        logger.debug("%s: could not compute median step", site_id)

    # -------------
    # Detector run
    # -------------
    try:
        detector = SchoolLeakDetector(df, site_id, cfg, up_to_date=up_to_date)

        # ✅ FIX: Restore FROZEN confidence values BEFORE running state_machine
        # This prevents recalculation of historical dates
        if prev_confidence_by_date and hasattr(detector, "confidence_by_date"):
            detector.confidence_by_date = prev_confidence_by_date.copy()
            logger.info(
                "%s: Restored %d FROZEN confidence values BEFORE state_machine",
                site_id,
                len(prev_confidence_by_date),
            )

        if prev_signal_components and hasattr(detector, "signal_components_by_date"):
            detector.signal_components_by_date = prev_signal_components.copy()
            logger.info(
                "%s: Restored %d signal components BEFORE state_machine",
                site_id,
                len(prev_signal_components),
            )

        if hasattr(detector, "preprocess"):
            detector.preprocess()
        if hasattr(detector, "state_machine"):
            detector.state_machine()
    except Exception:
        logger.exception("%s: detector failed during preprocess/state_machine", site_id)
        return site_id, None, pd.DataFrame()

    # Gather incidents & build confirmed_df (using imported canonize functions)
    incidents = []
    try:
        if hasattr(detector, "incidents") and detector.incidents:
            for inc in detector.incidents:
                try:
                    incidents.append(_canonize_incident(inc, site_id))
                except Exception:
                    logger.exception("%s: failed to canonize incident", site_id)
    except Exception:
        logger.exception("%s: accessing detector.incidents failed", site_id)

    # If detector provides a confirmed table, canonize it; otherwise derive a simple one
    confirmed_df = pd.DataFrame()
    try:
        if hasattr(detector, "confirmed_df") and detector.confirmed_df is not None:
            confirmed_df = _canonize_confirmed_df(detector.confirmed_df, site_id)
        else:
            # Derive lightweight confirmed table from incidents with status INVESTIGATE/CALL
            confirmed = [
                inc
                for inc in incidents
                if str(inc.get("status", "")).upper() in ("INVESTIGATE", "CALL")
            ]
            confirmed_df = pd.DataFrame(confirmed) if confirmed else pd.DataFrame()
            if not confirmed_df.empty:
                confirmed_df = _canonize_confirmed_df(confirmed_df, site_id)
    except Exception:
        logger.exception("%s: building confirmed_df failed", site_id)
        confirmed_df = pd.DataFrame()

    # Helpful trace when hitting a new confirmation "today"
    if up_to_date is not None and not confirmed_df.empty:
        try:
            today = pd.to_datetime(up_to_date).normalize()
            todays = confirmed_df.loc[
                confirmed_df.get("alert_date", pd.NaT).dt.normalize() == today
            ]
            for _, row in todays.iterrows():
                logger.info(
                    "Confirm @ %s | %s | sev=%s | conf=%s%%",
                    today.date(),
                    row.get("event_id"),
                    row.get("severity_max"),
                    (
                        f"{float(row.get('confidence', 0)):.0f}"
                        if pd.notna(row.get("confidence", np.nan))
                        else "?"
                    ),
                )
        except Exception:
            # non-fatal
            pass

    return site_id, detector, confirmed_df


def run_efficient_pipeline(
    school_dfs: dict, cfg: dict, leak_log_file=None, up_to_date=None
):
    total_schools = len(school_dfs)
    logging.info(
        f"--- Starting Efficient Leak Detection Pipeline for {total_schools} schools ---"
    )

    all_confirmed_leaks = []
    rejected_events = []

    # Load historical leak log if available
    leak_log = []
    if leak_log_file:
        try:
            leak_log = pd.read_csv(leak_log_file, parse_dates=["start", "end"]).to_dict(
                "records"
            )
            logging.info(
                f"Loaded {len(leak_log)} records from leak log: {leak_log_file}"
            )
        except FileNotFoundError:
            logging.warning(
                f"Leak log file not found at {leak_log_file}. Proceeding without leak log."
            )
        except Exception as e:
            logging.error(
                f"Error loading leak log file {leak_log_file}: {e}. Proceeding without leak log."
            )

    # Slice data if up_to_date
    if up_to_date:
        logging.info(f"Slicing data up to {pd.to_datetime(up_to_date).date()}")
        sliced_dfs = {
            sid: df[df["time"] <= pd.to_datetime(up_to_date)]
            for sid, df in school_dfs.items()
        }
    else:
        logging.info("Using full dataset (no cutoff applied).")
        sliced_dfs = school_dfs

    # Parallel processing across schools
    logging.info("Dispatching school datasets to worker processes...")
    max_workers = min(4, os.cpu_count() or 4)  # Cap at 4 workers
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        args_list = [
            (sid, df, cfg, leak_log, up_to_date) for sid, df in sliced_dfs.items()
        ]
        results = list(executor.map(process_site, args_list))

    site_detectors = {}
    site_confirmed_dfs = {}
    for idx, (school_id, detector, confirmed_df) in enumerate(results, start=1):
        if detector:
            logging.info(
                f"[{idx}/{total_schools}] Processed {school_id} "
                f"| {len(confirmed_df)} confirmed leaks detected"
            )
            site_detectors[school_id] = detector
            site_confirmed_dfs[school_id] = confirmed_df
            all_confirmed_leaks.extend(confirmed_df.to_dict("records"))
        else:
            logging.warning(
                f"[{idx}/{total_schools}] Skipped {school_id} (no detector returned)"
            )

    # Save confirmed leaks
    confirmed_df = pd.DataFrame(all_confirmed_leaks)
    export_path = os.path.join(cfg["export_folder"], "Efficient_Confirmed_Leaks.csv")
    os.makedirs(cfg["export_folder"], exist_ok=True)
    confirmed_df.to_csv(export_path, index=False)
    logging.info(
        f"✅ Completed pipeline: {len(confirmed_df)} confirmed leaks saved to {export_path}"
    )

    # Save rejected events if any
    if rejected_events:
        rejected_df = pd.DataFrame(rejected_events)
        rejected_path = os.path.join(cfg["export_folder"], "Rejected_Events.csv")
        rejected_df.to_csv(rejected_path, index=False)
        logging.info(
            f"⚠️ Rejected {len(rejected_events)} events. Saved to {rejected_path}"
        )

    # Save summary per site
    if not confirmed_df.empty:
        summary = (
            confirmed_df.groupby("site_id")
            .agg(
                num_leaks=("site_id", "size"),
                total_volume=("total_volume_L", "sum"),
                avg_duration=("duration_hours", "mean"),
            )
            .reset_index()
        )
        summary_path = os.path.join(cfg["export_folder"], "Leak_Summary.csv")
        summary.to_csv(summary_path, index=False)
        logging.info(f"📊 Summary report saved to {summary_path}")

    logging.info("--- Leak Detection Pipeline finished successfully ---")
    return confirmed_df


def validate_config(cfg):
    required_keys = [
        "night_start",
        "night_end",
        "after_hours_start",
        "after_hours_end",
        "baseline_window_days",
        "abs_floor_lph",
        "sustained_after_hours_delta_kl",
        "spike_multiplier",
        "spike_ref_percentile",
        "score_weights",
        "persistence_gates",
        "severity_bands_lph",
        "cusum_k",
        "cusum_h",
        "export_folder",
        "data_path",
        "save_dir",
    ]
    for key in required_keys:
        if key not in cfg:
            logging.error(f"Missing config key: {key}")
            raise KeyError(f"Missing config key: {key}")
    if cfg["night_start"] >= cfg["night_end"]:
        raise ValueError("night_start must be less than night_end")
    if cfg["abs_floor_lph"] <= 0:
        raise ValueError("abs_floor_lph must be positive")
    if not all(w > 0 for w in cfg["score_weights"].values()):
        raise ValueError("All score_weights must be positive")
    # Validate score_weights has all required signals
    expected_signals = {"MNF", "RESIDUAL", "CUSUM", "AFTERHRS", "BURSTBF"}
    if set(cfg["score_weights"].keys()) != expected_signals:
        raise ValueError(f"score_weights must have exactly {expected_signals}")


# %%

if __name__ == "__main__":
    with open("config_leak_detection.yml", "r") as f:
        cfg = yaml.safe_load(f)
    logging.info("Configuration loaded from config_leak_detection.yml")
    validate_config(cfg)

    # Load all sites
    school_dfs = load_tafe_data(cfg["data_path"])

    # --- Pick one property only ---
    target_site = "Property 11127"
    single_school_dfs = {target_site: school_dfs[target_site]}

    # Run pipeline just for this property
    confirmed_leaks = run_efficient_pipeline(
        single_school_dfs, cfg, leak_log_file=cfg.get("leak_log_path")
    )

    print(f"\n--- Confirmed Leaks for {target_site} ---")
    if confirmed_leaks.empty:
        print("No confirmed leaks found.")
    else:
        print(confirmed_leaks.to_string())


# %%
