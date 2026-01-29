# Modularized chart generation functions for leak detection
# Extracted from Model_1_realtime_simulation.py (Phase 3)

import pandas as pd
import numpy as np
from datetime import timedelta
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go


def create_confidence_evolution_mini(detector, incident):
    """Create mini bar chart showing confidence building over duration period"""
    import plotly.graph_objects as go

    # ✅ FIX: Use stored signal components to calculate confidence consistently
    # This prevents recalculation when events are extended
    dates = []
    confidences = []

    event_id = incident.get("event_id", "unknown")
    logging.info(f"[CHART] Creating confidence evolution for {event_id}")

    # PREFERRED: Use stored signal components from incident
    if (
        "signal_components_by_date" in incident
        and incident["signal_components_by_date"]
    ):
        start = pd.to_datetime(incident["start_day"])
        end = pd.to_datetime(incident["last_day"])

        logging.info(
            f"[CHART] {event_id}: Using STORED signal components for {start.date()} to {end.date()}"
        )
        logging.info(
            f"[CHART] {event_id}: Available dates in signal_components: {list(incident['signal_components_by_date'].keys())}"
        )

        try:
            for d in pd.date_range(start, end, freq="D"):
                d_key = d.strftime("%Y-%m-%d")
                if d_key in incident["signal_components_by_date"]:
                    comp = incident["signal_components_by_date"][d_key]

                    # ✅ FIX: Use FROZEN confidence if available, otherwise calculate
                    if "confidence" in comp:
                        conf = comp["confidence"]
                        logging.info(
                            f"[CHART] {event_id} - {d_key}: Using FROZEN confidence={conf:.1f}%"
                        )
                    else:
                        # Legacy fallback: calculate confidence with the RELATIVE persistence from start
                        persistence_days = (d - start).days + 1
                        conf = detector.get_confidence(
                            comp["sub_scores"],
                            persistence_days,
                            comp["deltaNF"],
                            comp["NF_MAD"],
                        )
                        logging.warning(
                            f"[CHART] {event_id} - {d_key}: No frozen confidence, recalculating (may be inconsistent)"
                        )

                    dates.append(d)
                    confidences.append(conf)

                    logging.info(
                        f"[CHART] {event_id} - {d_key}: deltaNF={comp['deltaNF']:.1f}, "
                        f"NF_MAD={comp['NF_MAD']:.1f}, conf={conf:.1f}%"
                    )
        except Exception as e:
            logging.error(f"[CHART] {event_id}: Error using signal components: {e}")
            pass

    # Fallback: Use legacy confidence_evolution_daily if available
    if not dates or not confidences:
        logging.warning(
            f"[CHART] {event_id}: No signal components found, trying legacy confidence_evolution_daily"
        )
        if (
            "confidence_evolution_daily" in incident
            and incident["confidence_evolution_daily"]
        ):
            try:
                for entry in incident["confidence_evolution_daily"]:
                    dates.append(pd.to_datetime(entry["date"]))
                    confidences.append(entry["confidence"])
                logging.info(
                    f"[CHART] {event_id}: Using legacy confidence_evolution_daily"
                )
            except Exception as e:
                logging.error(f"[CHART] {event_id}: Error using legacy data: {e}")
                pass

    # Final fallback: recalculate from scratch (DEPRECATED - will be inconsistent)
    if not dates or not confidences:
        logging.warning(
            f"[CHART] {event_id}: RECALCULATING from scratch (INCONSISTENT!)"
        )
        start = pd.to_datetime(incident["start_day"])
        end = pd.to_datetime(incident["last_day"])

        for i, d in enumerate(pd.date_range(start, end, freq="D")):
            if d not in detector.daily.index:
                continue

            try:
                sub_scores, _, deltaNF, NF_MAD = detector.signals_and_score(d)
                persistence_days = (d - start).days + 1
                conf = detector.get_confidence(
                    sub_scores, persistence_days, deltaNF, NF_MAD
                )

                dates.append(d)
                confidences.append(conf)

                logging.warning(
                    f"[CHART] {event_id} - {d.strftime('%Y-%m-%d')}: RECALC persist={persistence_days}, "
                    f"deltaNF={deltaNF:.1f}, conf={conf:.1f}%"
                )
            except Exception:
                continue

    # Create figure
    fig = go.Figure()

    # Log the final confidence values that will be plotted
    if dates and confidences:
        conf_summary = ", ".join(
            [f"{d.strftime('%m-%d')}:{c:.0f}%" for d, c in zip(dates, confidences)]
        )
        logging.info(
            f"[CHART] {event_id}: FINAL confidence values: [{conf_summary}]"
        )

    if dates and confidences:
        # Color bars based on confidence level
        bar_colors = [
            (
                "rgb(255,0,0)"
                if c < 50
                else "rgb(255,165,0)" if c < 70 else "rgb(0,255,0)"
            )
            for c in confidences
        ]

        fig.add_trace(
            go.Bar(
                x=dates,
                y=confidences,
                marker=dict(color=bar_colors, line=dict(width=1, color="white")),
                text=[f"{c:.0f}%" for c in confidences],
                textposition="outside",
                textfont=dict(size=10, color="white"),
                hovertemplate="<b>Day %{x|%b %d}</b><br>Confidence: %{y:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        xaxis=dict(
            title="",
            showgrid=False,
            tickformat="%b %d",
        ),
        yaxis=dict(
            title="Confidence %",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            range=[0, 110],  # Extra space for text labels on top
        ),
        template="plotly_dark",
        height=200,
        margin=dict(l=50, r=20, t=20, b=30),
        paper_bgcolor="rgba(30,30,30,1)",
        plot_bgcolor="rgba(20,20,20,1)",
        showlegend=False,
    )

    return fig


def to_plotly_figs(detector, incident, window_days=30):
    """
    Generate enhanced professional charts for national dashboard use.

    Returns 4 figures:
    1. Anomaly Timeline (replaces simple flow chart)
    2. MNF Control Chart (replaces simple night flow trend)
    3. After-Hours Breakdown (replaces simple after-hours trend)
    4. Weekly Heatmap (enhanced version)
    """
    start = pd.to_datetime(incident["start_day"])
    end = pd.to_datetime(incident["last_day"])
    alert_date = pd.to_datetime(incident.get("alert_date", end))

    half_window = window_days // 2
    window_start = start - timedelta(days=half_window)
    window_end = end + timedelta(days=half_window)

    # Filter daily summaries
    daily_window = detector.daily[
        (detector.daily.index >= window_start) & (detector.daily.index <= window_end)
    ]

    # Filter raw hourly data
    df_window = detector.df[
        (detector.df.index >= window_start) & (detector.df.index <= window_end)
    ]

    # 1. Enhanced Anomaly Timeline
    flow_fig = _create_anomaly_timeline(
        detector, df_window, daily_window, incident, start, end, alert_date
    )

    # 2. MNF Control Chart
    mnf_fig = _create_mnf_control_chart(
        detector, daily_window, incident, start, end, alert_date
    )

    # 3. After-Hours Breakdown
    ah_fig = _create_after_hours_breakdown(
        detector, df_window, daily_window, incident, start, end, alert_date
    )

    # 4. Enhanced Weekly Heatmap
    heatmap = _create_enhanced_heatmap(df_window, start, end)

    return flow_fig, mnf_fig, ah_fig, heatmap


def _create_anomaly_timeline(
    detector, df_window, daily_window, incident, start, end, alert_date
):
    """
    Simplified flow timeline for non-technical users.
    Shows water usage over time with clear indication of the leak period.
    """

    # Calculate baseline (normal) flow level
    baseline_nf = detector.theta_min if detector.theta_min else detector.cfg["abs_floor_lph"]

    # Get the maximum flow during the leak for scaling
    leak_mask = (df_window.index >= start) & (df_window.index <= end)
    max_leak_flow = (
        df_window.loc[leak_mask, "flow"].max()
        if leak_mask.any()
        else baseline_nf * 2
    )

    fig = go.Figure()

    # Split data into before leak, during leak, and after leak for clearer visualization
    before_leak = df_window[df_window.index < start]
    during_leak = df_window[(df_window.index >= start) & (df_window.index <= end)]
    after_leak = df_window[df_window.index > end]

    # 1. Normal period flow (before leak) - Blue
    if not before_leak.empty:
        fig.add_trace(
            go.Scatter(
                x=before_leak.index,
                y=before_leak["flow"],
                mode="lines",
                name="Normal Usage",
                line=dict(color="rgb(100,180,255)", width=2),
                fill="tozeroy",
                fillcolor="rgba(100,180,255,0.2)",
                hovertemplate="<b>%{x|%b %d, %H:%M}</b><br>Water Flow: %{y:.0f} L/h<extra></extra>",
            )
        )

    # 2. Leak period flow - Red (highlighted)
    if not during_leak.empty:
        fig.add_trace(
            go.Scatter(
                x=during_leak.index,
                y=during_leak["flow"],
                mode="lines",
                name="🚨 Leak Period",
                line=dict(color="rgb(255,80,80)", width=3),
                fill="tozeroy",
                fillcolor="rgba(255,80,80,0.3)",
                hovertemplate="<b>%{x|%b %d, %H:%M}</b><br>⚠️ Water Flow: %{y:.0f} L/h<extra></extra>",
            )
        )

    # 3. After leak period (if any) - Blue
    if not after_leak.empty:
        fig.add_trace(
            go.Scatter(
                x=after_leak.index,
                y=after_leak["flow"],
                mode="lines",
                name="After Leak",
                line=dict(color="rgb(100,180,255)", width=2),
                fill="tozeroy",
                fillcolor="rgba(100,180,255,0.2)",
                hovertemplate="<b>%{x|%b %d, %H:%M}</b><br>Water Flow: %{y:.0f} L/h<extra></extra>",
                showlegend=False,
            )
        )

    # Add a simple "Normal Level" reference line
    fig.add_hline(
        y=baseline_nf,
        line_dash="dash",
        line_color="rgba(0,200,100,0.8)",
        line_width=2,
        annotation_text=f"✓ Normal Level ({baseline_nf:.0f} L/h)",
        annotation_position="top left",
        annotation=dict(
            font_size=12,
            bgcolor="rgba(0,100,50,0.8)",
            font_color="white",
            yshift=15,
        ),
    )

    # Add leak start marker with annotation
    fig.add_vline(
        x=start, line_color="rgba(255,165,0,0.8)", line_width=2, line_dash="dot"
    )
    fig.add_annotation(
        x=start,
        y=max_leak_flow * 0.95,
        text="⚠️ Leak Started",
        showarrow=True,
        arrowhead=2,
        arrowcolor="orange",
        font=dict(size=11, color="orange"),
        bgcolor="rgba(0,0,0,0.7)",
        bordercolor="orange",
        borderwidth=1,
    )

    # Add alert confirmation marker
    fig.add_vline(
        x=alert_date,
        line_color="rgba(255,50,50,0.9)",
        line_width=3,
        line_dash="solid",
    )
    fig.add_annotation(
        x=alert_date,
        y=max_leak_flow * 0.8,
        text="🔔 Alert Raised",
        showarrow=True,
        arrowhead=2,
        arrowcolor="red",
        font=dict(size=11, color="white"),
        bgcolor="rgba(200,0,0,0.8)",
        bordercolor="red",
        borderwidth=1,
    )

    # Calculate water loss for display
    delta_nf = incident.get("max_deltaNF", 0)
    vol_lost = incident.get("volume_lost_kL", incident.get("ui_total_volume_kL", 0))

    # Simple, clear layout
    fig.update_layout(
        title=dict(
            text=f"<b>💧 Water Usage Timeline</b><br>"
            f"<span style='font-size:12px;color:#aaa'>"
            f"Leak detected: {start.strftime('%b %d')} → {end.strftime('%b %d, %Y')} | "
            f"Extra flow: ~{delta_nf:.0f} L/h | Water lost: ~{vol_lost:.1f} kL</span>",
            font=dict(size=16, color="white"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            tickformat="%b %d",
        ),
        yaxis=dict(
            title="Water Flow (Litres per Hour)",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            rangemode="tozero",
        ),
        template="plotly_dark",
        hovermode="x unified",
        autosize=True,
        margin=dict(l=70, r=30, t=100, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30,30,30,0.9)",
            font=dict(size=11),
        ),
        paper_bgcolor="rgba(30,30,30,1)",
        plot_bgcolor="rgba(25,25,35,1)",
    )

    return fig


def _create_mnf_control_chart(detector, daily_window, incident, start, end, alert_date):
    """
    Simplified Night Flow comparison chart for non-technical users.
    Shows daily night-time water usage with clear normal vs abnormal indication.
    """

    # Calculate baseline (normal) from pre-incident data
    pre_incident = detector.daily[detector.daily.index < start]
    if len(pre_incident) < 10:
        pre_incident = detector.daily[detector.daily.index < end]

    baseline = (
        detector.robust_median(pre_incident["NF_d"]) if len(pre_incident) > 0 else 0
    )

    # Define simple threshold: 50% above baseline is concerning
    concern_level = baseline * 1.5

    fig = go.Figure()

    # Split data: before leak, during leak
    before_leak = daily_window[daily_window.index < start]
    during_leak = daily_window[
        (daily_window.index >= start) & (daily_window.index <= end)
    ]
    after_leak = daily_window[daily_window.index > end]

    # Normal period bars (before leak) - Blue
    if not before_leak.empty:
        fig.add_trace(
            go.Bar(
                x=before_leak.index,
                y=before_leak["NF_d"],
                name="Normal Period",
                marker_color="rgb(100,180,255)",
                hovertemplate="<b>%{x|%b %d}</b><br>Night Flow: %{y:.0f} L/h<extra></extra>",
            )
        )

    # Leak period bars - Red
    if not during_leak.empty:
        fig.add_trace(
            go.Bar(
                x=during_leak.index,
                y=during_leak["NF_d"],
                name="🚨 Leak Period",
                marker_color="rgb(255,80,80)",
                hovertemplate="<b>%{x|%b %d}</b><br>⚠️ Night Flow: %{y:.0f} L/h<extra></extra>",
            )
        )

    # After leak bars (if any) - Blue
    if not after_leak.empty:
        fig.add_trace(
            go.Bar(
                x=after_leak.index,
                y=after_leak["NF_d"],
                name="After Leak",
                marker_color="rgb(100,180,255)",
                showlegend=False,
                hovertemplate="<b>%{x|%b %d}</b><br>Night Flow: %{y:.0f} L/h<extra></extra>",
            )
        )

    # Normal baseline reference
    fig.add_hline(
        y=baseline,
        line_dash="dash",
        line_color="rgba(0,200,100,0.8)",
        line_width=2,
        annotation_text=f"✓ Normal ({baseline:.0f} L/h)",
        annotation_position="top left",
        annotation=dict(
            font_size=12,
            bgcolor="rgba(0,100,50,0.8)",
            font_color="white",
            yshift=15,
        ),
    )

    # Calculate average during leak
    if not during_leak.empty:
        leak_avg = during_leak["NF_d"].mean()
        increase = leak_avg - baseline
        increase_pct = (increase / baseline * 100) if baseline > 0 else 0

        # Add annotation showing the increase
        fig.add_annotation(
            x=during_leak.index[len(during_leak) // 2],
            y=leak_avg,
            text=f"📈 +{increase:.0f} L/h<br>(+{increase_pct:.0f}% above normal)",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            font=dict(size=11, color="white"),
            bgcolor="rgba(200,0,0,0.85)",
            bordercolor="red",
            borderwidth=1,
        )

    fig.update_layout(
        title=dict(
            text="<b>🌙 Night-Time Water Usage (12am-4am)</b>",
            font=dict(size=14, color="white"),
            x=0.5,
            xanchor="center",
            y=0.95,
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            tickformat="%b %d",
        ),
        yaxis=dict(
            title="Night Flow (L/h)",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            rangemode="tozero",
        ),
        template="plotly_dark",
        autosize=True,
        hovermode="x unified",
        margin=dict(l=60, r=30, t=70, b=50),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30,30,30,0.9)",
        ),
        bargap=0.15,
        paper_bgcolor="rgba(30,30,30,1)",
        plot_bgcolor="rgba(25,25,35,1)",
    )

    return fig


def _create_after_hours_breakdown(
    detector, df_window, daily_window, incident, start, end, alert_date
):
    """
    Simplified After-Hours usage chart for non-technical users.
    Shows daily after-hours consumption with clear comparison to expected levels.
    """

    # Aggregate daily after-hours usage (simplified: just total after hours)
    daily_data = []
    window_start = df_window.index.min()
    window_end = df_window.index.max()

    for d in pd.date_range(window_start.date(), window_end.date(), freq="D"):
        day_data = df_window[df_window.index.date == d.date()]

        if len(day_data) == 0:
            continue

        # After hours: before 7am OR after 4pm
        after_hours = (
            day_data[(day_data.index.hour < 7) | (day_data.index.hour >= 16)][
                "flow"
            ].sum()
            / 1000
        )  # Convert to kL

        is_leak = start.date() <= d.date() <= end.date()

        daily_data.append(
            {
                "date": d,
                "after_hours_kL": after_hours,
                "is_leak": is_leak,
            }
        )

    if not daily_data:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark", autosize=True)
        return fig

    df_daily = pd.DataFrame(daily_data)

    # Calculate baseline from non-leak days
    normal_days = df_daily[~df_daily["is_leak"]]
    baseline_kL = (
        normal_days["after_hours_kL"].median() if len(normal_days) > 0 else 0
    )

    fig = go.Figure()

    # Normal period bars - Blue
    normal_data = df_daily[~df_daily["is_leak"]]
    if not normal_data.empty:
        fig.add_trace(
            go.Bar(
                x=normal_data["date"],
                y=normal_data["after_hours_kL"],
                name="Normal Days",
                marker_color="rgb(100,180,255)",
                hovertemplate="<b>%{x|%b %d}</b><br>After-Hours: %{y:.1f} kL<extra></extra>",
            )
        )

    # Leak period bars - Red
    leak_data = df_daily[df_daily["is_leak"]]
    if not leak_data.empty:
        fig.add_trace(
            go.Bar(
                x=leak_data["date"],
                y=leak_data["after_hours_kL"],
                name="🚨 Leak Period",
                marker_color="rgb(255,80,80)",
                hovertemplate="<b>%{x|%b %d}</b><br>⚠️ After-Hours: %{y:.1f} kL<extra></extra>",
            )
        )

    # Normal baseline reference
    fig.add_hline(
        y=baseline_kL,
        line_dash="dash",
        line_color="rgba(0,200,100,0.8)",
        line_width=2,
        annotation_text=f"✓ Normal ({baseline_kL:.1f} kL/day)",
        annotation_position="top left",
        annotation=dict(
            font_size=12, bgcolor="rgba(0,100,50,0.8)", font_color="white"
        ),
    )

    # Calculate and show excess during leak
    if not leak_data.empty:
        total_leak = leak_data["after_hours_kL"].sum()
        expected = baseline_kL * len(leak_data)
        excess = total_leak - expected

        if excess > 0:
            # Add summary annotation
            fig.add_annotation(
                x=leak_data["date"].iloc[-1],
                y=leak_data["after_hours_kL"].max() * 1.1,
                text=f"💧 Extra water used:<br><b>{excess:.1f} kL</b><br>(~${excess * 2:.0f} cost)",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
                font=dict(size=11, color="white"),
                bgcolor="rgba(200,0,0,0.85)",
                bordercolor="red",
                borderwidth=1,
            )

    fig.update_layout(
        title=dict(
            text="<b>🕐 After-Hours Water Usage (Before 7am & After 4pm)</b>",
            font=dict(size=14, color="white"),
            x=0.5,
            xanchor="center",
            y=0.95,
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            tickformat="%b %d",
        ),
        yaxis=dict(
            title="Water Used (kL)",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            rangemode="tozero",
        ),
        template="plotly_dark",
        autosize=True,
        hovermode="x unified",
        margin=dict(l=60, r=30, t=70, b=70),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30,30,30,0.9)",
        ),
        bargap=0.15,
        paper_bgcolor="rgba(30,30,30,1)",
        plot_bgcolor="rgba(25,25,35,1)",
    )

    return fig


def _create_enhanced_heatmap(df_window, start, end):
    """
    Simplified Pattern Analysis for non-technical users.
    Shows when water is being used unexpectedly with clear visual indicators.
    """

    df_reset = df_window.reset_index()
    df_reset["time"] = pd.to_datetime(df_reset["time"])

    # Split into normal period and leak period
    normal_data = df_reset[df_reset["time"] < start]
    leak_data = df_reset[(df_reset["time"] >= start) & (df_reset["time"] <= end)]

    # Create time period categories (simplified from 24 hours)
    def get_time_period(hour):
        if 0 <= hour < 4:
            return "🌙 Night (12am-4am)"
        elif 4 <= hour < 7:
            return "🌅 Early Morning (4am-7am)"
        elif 7 <= hour < 16:
            return "☀️ Business Hours (7am-4pm)"
        else:
            return "🌆 Evening (4pm-12am)"

    time_periods = [
        "🌙 Night (12am-4am)",
        "🌅 Early Morning (4am-7am)",
        "☀️ Business Hours (7am-4pm)",
        "🌆 Evening (4pm-12am)",
    ]

    # Calculate average flow by time period for normal vs leak
    def calc_period_averages(data):
        if data.empty:
            return {p: 0 for p in time_periods}
        data = data.copy()
        data["period"] = data["time"].dt.hour.apply(get_time_period)
        return data.groupby("period")["flow"].mean().to_dict()

    normal_avgs = calc_period_averages(normal_data)
    leak_avgs = calc_period_averages(leak_data)

    # Prepare data for grouped bar chart
    normal_values = [normal_avgs.get(p, 0) for p in time_periods]
    leak_values = [leak_avgs.get(p, 0) for p in time_periods]

    fig = go.Figure()

    # Normal period bars
    fig.add_trace(
        go.Bar(
            name="Normal Period",
            x=time_periods,
            y=normal_values,
            marker_color="rgb(100,180,255)",
            text=[f"{v:.0f}" for v in normal_values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Normal: %{y:.0f} L/h<extra></extra>",
        )
    )

    # Leak period bars
    fig.add_trace(
        go.Bar(
            name="🚨 Leak Period",
            x=time_periods,
            y=leak_values,
            marker_color="rgb(255,80,80)",
            text=[f"{v:.0f}" for v in leak_values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Leak Period: %{y:.0f} L/h<extra></extra>",
        )
    )

    # Calculate the biggest increase
    increases = []
    for i, period in enumerate(time_periods):
        normal_val = normal_values[i]
        leak_val = leak_values[i]
        if normal_val > 0:
            pct_increase = ((leak_val - normal_val) / normal_val) * 100
        else:
            pct_increase = 100 if leak_val > 0 else 0
        increases.append((period, leak_val - normal_val, pct_increase))

    # Find the period with biggest absolute increase
    max_increase = max(increases, key=lambda x: x[1])

    # Add annotation for biggest problem area
    if max_increase[1] > 0:
        problem_idx = time_periods.index(max_increase[0])
        fig.add_annotation(
            x=max_increase[0],
            y=leak_values[problem_idx] * 1.15,
            text=f"⚠️ Biggest increase!<br>+{max_increase[1]:.0f} L/h ({max_increase[2]:.0f}%)",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            font=dict(size=11, color="white"),
            bgcolor="rgba(200,0,0,0.85)",
            bordercolor="red",
            borderwidth=1,
        )

    # Add "expected to be low" annotation for night hours
    fig.add_annotation(
        x="🌙 Night (12am-4am)",
        y=(
            max(normal_values[0], leak_values[0]) * 0.5
            if max(normal_values[0], leak_values[0]) > 0
            else 50
        ),
        text="Should be<br>near zero",
        showarrow=False,
        font=dict(size=9, color="rgba(200,200,200,0.7)"),
        bgcolor="rgba(0,0,0,0.5)",
    )

    # Calculate summary stats
    total_normal = (
        sum(normal_values) * len(normal_data) / max(len(normal_data), 1)
        if normal_data.any
        else 0
    )
    total_leak = (
        sum(leak_values) * len(leak_data) / max(len(leak_data), 1)
        if not leak_data.empty
        else 0
    )

    fig.update_layout(
        title=dict(
            text="<b>📊 Water Usage Pattern: Normal vs Leak Period</b>",
            font=dict(size=14, color="white"),
            x=0.5,
            xanchor="center",
            y=0.97,
        ),
        xaxis=dict(
            title="",
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Avg Flow (L/h)",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            rangemode="tozero",
        ),
        barmode="group",
        template="plotly_dark",
        autosize=True,
        margin=dict(l=60, r=30, t=60, b=160),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30,30,30,0.9)",
        ),
        bargap=0.2,
        bargroupgap=0.1,
        paper_bgcolor="rgba(30,30,30,1)",
        plot_bgcolor="rgba(25,25,35,1)",
    )

    # Add a text box with key insight
    night_increase = leak_values[0] - normal_values[0]
    if night_increase > 10:
        insight_text = f"💡 Key Finding: Night-time usage increased by {night_increase:.0f} L/h. This suggests a leak (buildings should have minimal water use at night)."
    elif max_increase[1] > 10:
        insight_text = f"💡 Key Finding: Biggest increase during {max_increase[0].split(' ')[1]} (+{max_increase[1]:.0f} L/h more than normal)."
    else:
        insight_text = (
            "💡 Usage patterns appear relatively normal across all time periods."
        )

    fig.add_annotation(
        x=0.5,
        y=-0.48,
        xref="paper",
        yref="paper",
        text=insight_text,
        showarrow=False,
        font=dict(size=10, color="rgba(200,200,200,0.9)"),
        bgcolor="rgba(50,50,70,0.8)",
        bordercolor="rgba(100,100,150,0.5)",
        borderwidth=1,
        borderpad=6,
        align="center",
    )

    return fig


def plot_leak_event_matplotlib(detector, incident, site_cfg):
    """
    Enhanced leak event plot using matplotlib:
    - Shows pre-leak midnight flow (blue)
    - Shows confirmation period (orange)
    - Marks the day leak is confirmed
    """
    import os

    start_time = pd.Timestamp(incident["start_day"])
    end_time = pd.Timestamp(incident["last_day"])
    save_dir = detector.cfg["save_dir"]

    # Define plot window: ±10 days
    plot_start = start_time - timedelta(days=10)
    plot_end = end_time + timedelta(days=10)
    plot_data = detector.df[
        (detector.df.index >= plot_start) & (detector.df.index <= plot_end)
    ].copy()
    if plot_data.empty:
        logging.warning(
            f"No data to plot for {detector.site_id} on {start_time.date()}"
        )
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # Flow trace
    ax.plot(
        plot_data.index,
        plot_data["flow"],
        label="Hourly Flow (L/h)",
        color="dodgerblue",
        alpha=0.7,
    )

    # MNF threshold
    ax.axhline(
        y=site_cfg["theta_min"],
        color="black",
        linestyle="--",
        linewidth=1.2,
        alpha=0.7,
        label=f"MNF Threshold ({site_cfg['theta_min']:.1f} L/h)",
    )

    # Pre-leak midnight flow (blue shade, 2 days before start)
    for offset in range(2, 0, -1):
        pre_day = (start_time - timedelta(days=offset)).floor("D")
        t0 = pre_day.replace(hour=0, minute=0)
        t1 = t0 + timedelta(hours=4)
        ax.axvspan(
            t0,
            t1,
            color="skyblue",
            alpha=0.3,
            label="Pre-leak midnight flow" if offset == 2 else None,
        )

    # Leak window (red shade)
    ax.axvspan(
        start_time, end_time, color="red", alpha=0.2, label="Red = Confirmed Leak"
    )

    # Confirmation period (orange shade)
    days_needed = max(
        3,
        detector.get_persistence_needed(
            incident["max_deltaNF"],
            len(incident["reason_codes"]),
            incident["confidence"],
        ),
    )
    computed_alert = start_time + timedelta(days=days_needed - 1)
    alert_date = pd.to_datetime(incident.get("alert_date", computed_alert))

    ax.axvspan(
        start_time,
        alert_date,
        color="orange",
        alpha=0.3,
        label=f"Confirmation period ({days_needed} days)",
    )

    ax.axvline(
        alert_date,
        color="green",
        linestyle="--",
        linewidth=2,
        label="Leak confirmed (alert date)",
    )

    # Labels & formatting
    ax.set_title(
        f"Site: {detector.site_id} - Leak Event\n{start_time.date()} to {end_time.date()}"
    )
    ax.set_ylabel("Flow (L/h)")
    ax.set_xlabel("Timestamp")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b %H:%M"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.tight_layout()

    # Save
    folder = os.path.join(save_dir, detector.site_id)
    os.makedirs(folder, exist_ok=True)
    filename = f"Leak_{detector.site_id}_{start_time.strftime('%Y-%m-%d')}.png"
    plt.savefig(os.path.join(folder, filename))
    plt.close()
    logging.info(f"Enhanced plot saved: {os.path.join(folder, filename)}")
