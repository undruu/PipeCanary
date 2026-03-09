from dataclasses import dataclass

import numpy as np


@dataclass
class AnomalyResult:
    is_anomaly: bool
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float | None = None
    pct_change: float | None = None
    message: str = ""


class AnomalyDetector:
    """Statistical anomaly detection for data quality metrics."""

    @staticmethod
    def detect_row_count_anomaly(
        current_count: float,
        historical_counts: list[float],
        z_threshold: float = 3.0,
    ) -> AnomalyResult:
        """Detect row count anomalies using z-score against a trailing window.

        Args:
            current_count: The current row count.
            historical_counts: Historical row counts (trailing 14-day window).
            z_threshold: Z-score threshold for anomaly detection (default: 3.0).
        """
        if len(historical_counts) < 2:
            return AnomalyResult(
                is_anomaly=False,
                current_value=current_count,
                baseline_mean=current_count,
                baseline_std=0,
                message="Insufficient history for anomaly detection",
            )

        arr = np.array(historical_counts)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std == 0:
            is_anomaly = current_count != mean
            return AnomalyResult(
                is_anomaly=is_anomaly,
                current_value=current_count,
                baseline_mean=mean,
                baseline_std=std,
                z_score=None,
                message="Zero variance in historical data" if is_anomaly else "Stable",
            )

        z_score = (current_count - mean) / std

        is_anomaly = abs(z_score) > z_threshold
        direction = "above" if z_score > 0 else "below"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            current_value=current_count,
            baseline_mean=mean,
            baseline_std=std,
            z_score=float(z_score),
            message=f"Row count is {abs(z_score):.1f} std devs {direction} the mean" if is_anomaly else "Normal",
        )

    @staticmethod
    def detect_null_rate_anomaly(
        current_rate: float,
        historical_rates: list[float],
        multiplier_threshold: float = 2.0,
    ) -> AnomalyResult:
        """Detect null rate anomalies using percentage change against baseline.

        Args:
            current_rate: Current null rate (0.0 to 1.0).
            historical_rates: Historical null rates (trailing 7-day window).
            multiplier_threshold: Alert if current rate exceeds this multiple of the baseline.
        """
        if len(historical_rates) < 1:
            return AnomalyResult(
                is_anomaly=False,
                current_value=current_rate,
                baseline_mean=current_rate,
                baseline_std=0,
                message="Insufficient history for anomaly detection",
            )

        arr = np.array(historical_rates)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0

        if mean == 0:
            is_anomaly = current_rate > 0
            return AnomalyResult(
                is_anomaly=is_anomaly,
                current_value=current_rate,
                baseline_mean=mean,
                baseline_std=std,
                pct_change=None,
                message="Null rate appeared where none existed before" if is_anomaly else "No nulls",
            )

        pct_change = current_rate / mean

        is_anomaly = pct_change >= multiplier_threshold

        return AnomalyResult(
            is_anomaly=is_anomaly,
            current_value=current_rate,
            baseline_mean=mean,
            baseline_std=std,
            pct_change=float(pct_change),
            message=f"Null rate is {pct_change:.1f}x the baseline average" if is_anomaly else "Normal",
        )

    @staticmethod
    def detect_cardinality_anomaly(
        current_count: float,
        historical_counts: list[float],
        z_threshold: float = 3.0,
    ) -> AnomalyResult:
        """Detect cardinality anomalies (sudden drops or spikes in distinct values).

        Uses z-score against a trailing window, same approach as row count.
        """
        if len(historical_counts) < 2:
            return AnomalyResult(
                is_anomaly=False,
                current_value=current_count,
                baseline_mean=current_count,
                baseline_std=0,
                message="Insufficient history for anomaly detection",
            )

        arr = np.array(historical_counts)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std == 0:
            is_anomaly = current_count != mean
            return AnomalyResult(
                is_anomaly=is_anomaly,
                current_value=current_count,
                baseline_mean=mean,
                baseline_std=std,
                z_score=None,
                message="Cardinality changed from a previously constant value" if is_anomaly else "Stable",
            )

        z_score = (current_count - mean) / std
        is_anomaly = abs(z_score) > z_threshold
        direction = "above" if z_score > 0 else "below"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            current_value=current_count,
            baseline_mean=mean,
            baseline_std=std,
            z_score=float(z_score),
            message=f"Cardinality is {abs(z_score):.1f} std devs {direction} the mean" if is_anomaly else "Normal",
        )
