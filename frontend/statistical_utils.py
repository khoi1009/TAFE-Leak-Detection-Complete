"""
Statistical utility functions for leak detection.
Pure functions with no side effects - extracted from SchoolLeakDetector.
"""
import numpy as np


def robust_median(series) -> float:
    """Calculate median, returning 0 for empty series."""
    return np.median(series) if len(series) > 0 else 0


def robust_mad(series) -> float:
    """Calculate Median Absolute Deviation."""
    med = robust_median(series)
    return np.median(np.abs(series - med)) if len(series) > 0 else 0


def detect_cusum(series, k: float, h: float, mad: float) -> int:
    """
    CUSUM control chart detection.
    Returns 1 if any cumulative sum exceeds threshold, 0 otherwise.
    """
    mean = np.mean(series)
    s_plus = np.zeros(len(series))
    for i in range(1, len(series)):
        s_plus[i] = max(0, s_plus[i - 1] + (series[i] - mean - k * mad))
    return 1 if np.any(s_plus > h * mad) else 0
