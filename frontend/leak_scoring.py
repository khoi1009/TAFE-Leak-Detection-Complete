"""
Leak scoring and categorization functions.
Pure functions - no class state required. Extracted from SchoolLeakDetector.
"""
from typing import Dict, Tuple


def get_severity(delta_nf: float, severity_bands: dict) -> str:
    """
    Map deltaNF to severity band (S1-S5).

    Args:
        delta_nf: Night flow delta in L/h
        severity_bands: Dict like {"S1": [0, 200], "S2": [200, 1000], ...}

    Returns:
        Severity string like "S1", "S2", etc.
    """
    for s, (low, high) in severity_bands.items():
        if low <= delta_nf < high:
            return s
    return "S5" if delta_nf >= 10000 else "S1"


def get_confidence(
    sub_scores: Dict[str, float],
    persistence_days: int,
    delta_nf: float,
    nf_mad: float
) -> float:
    """
    Calculate confidence score (0-100).

    Components:
    - Signal-to-noise ratio (30%)
    - Persistence (30%)
    - Signal agreement (40%)
    """
    sig_agree = sum(1 for v in sub_scores.values() if v >= 0.7)
    snr = delta_nf / max(nf_mad, 1)
    norm_snr = min(1, snr / 10)
    norm_persist = min(1, persistence_days / 10)
    norm_agree = sig_agree / 5
    confidence = (0.3 * norm_snr + 0.3 * norm_persist + 0.4 * norm_agree) * 100
    return min(100, max(0, confidence))


def get_persistence_needed(
    delta_nf: float,
    sig_agree: int,
    confidence: float,
    persistence_gates: dict
) -> int:
    """
    Determine days needed to confirm leak based on severity.

    Args:
        delta_nf: Night flow delta in L/h
        sig_agree: Number of signals agreeing (count)
        confidence: Current confidence %
        persistence_gates: Dict with thresholds like {"<100": {...}, ...}

    Returns:
        Minimum days needed (at least 3)
    """
    if delta_nf < 100:
        gate = persistence_gates["<100"]
    elif delta_nf < 200:
        gate = persistence_gates["100-200"]
    elif delta_nf < 1000:
        gate = persistence_gates["200-1000"]
    else:
        gate = persistence_gates[">=1000"]

    needed = (
        gate["fast_min"]
        if sig_agree >= 3 and confidence >= 70
        else gate["default_max"]
    )
    return max(3, needed)


def categorize_leak(
    avg_flow: float,
    std_dev: float,
    baseline: float
) -> Tuple[str, str]:
    """
    Categorize leak type based on flow characteristics.

    Returns:
        Tuple of (category_name, description)
    """
    fixture_thresh = 2 * baseline
    pipe_thresh = 5 * baseline
    burst_thresh = 10 * baseline

    if avg_flow <= fixture_thresh and std_dev < 0.2 * fixture_thresh:
        return (
            "Fixture Leak",
            f"Low, steady flow <{fixture_thresh:.0f} L/h. Likely toilets/taps."
        )
    elif avg_flow <= pipe_thresh and std_dev < 0.3 * pipe_thresh:
        return (
            "Underground/Pipework Leak",
            f"Persistent steady flow <{pipe_thresh:.0f} L/h."
        )
    elif avg_flow <= burst_thresh and std_dev >= 0.3 * pipe_thresh:
        return (
            "Appliance/Cycling Fault",
            f"Erratic pattern <{burst_thresh:.0f} L/h. Possible appliances."
        )
    else:
        return (
            "Large Burst/Event",
            f"Very high flow >{burst_thresh:.0f} L/h. Likely major pipe break."
        )
