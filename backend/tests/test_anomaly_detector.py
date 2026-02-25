from app.anomaly.detector import AnomalyDetector


class TestRowCountAnomaly:
    def test_insufficient_history(self):
        result = AnomalyDetector.detect_row_count_anomaly(100, [100])
        assert not result.is_anomaly
        assert "Insufficient" in result.message

    def test_normal_value(self):
        historical = [100, 102, 98, 101, 99, 103, 97, 100, 102, 98, 101, 99, 103, 97]
        result = AnomalyDetector.detect_row_count_anomaly(101, historical)
        assert not result.is_anomaly

    def test_anomaly_detected(self):
        historical = [100, 102, 98, 101, 99, 103, 97, 100, 102, 98, 101, 99, 103, 97]
        result = AnomalyDetector.detect_row_count_anomaly(200, historical)
        assert result.is_anomaly
        assert result.z_score is not None
        assert abs(result.z_score) > 3.0

    def test_zero_variance(self):
        historical = [100, 100, 100, 100]
        result = AnomalyDetector.detect_row_count_anomaly(100, historical)
        assert not result.is_anomaly

    def test_zero_variance_with_change(self):
        historical = [100, 100, 100, 100]
        result = AnomalyDetector.detect_row_count_anomaly(101, historical)
        assert result.is_anomaly


class TestNullRateAnomaly:
    def test_insufficient_history(self):
        result = AnomalyDetector.detect_null_rate_anomaly(0.05, [0.05])
        assert not result.is_anomaly

    def test_normal_null_rate(self):
        historical = [0.05, 0.04, 0.06, 0.05, 0.04, 0.05, 0.06]
        result = AnomalyDetector.detect_null_rate_anomaly(0.05, historical)
        assert not result.is_anomaly

    def test_null_rate_spike(self):
        historical = [0.05, 0.04, 0.06, 0.05, 0.04, 0.05, 0.06]
        result = AnomalyDetector.detect_null_rate_anomaly(0.50, historical)
        assert result.is_anomaly
        assert result.pct_change is not None
        assert result.pct_change > 2.0

    def test_null_rate_from_zero(self):
        historical = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = AnomalyDetector.detect_null_rate_anomaly(0.1, historical)
        assert result.is_anomaly

    def test_null_rate_stays_zero(self):
        historical = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = AnomalyDetector.detect_null_rate_anomaly(0.0, historical)
        assert not result.is_anomaly


class TestCardinalityAnomaly:
    def test_stable_cardinality(self):
        historical = [1000, 1005, 998, 1002, 999, 1001, 1003, 997, 1004, 1000, 1002, 998, 1001, 999]
        result = AnomalyDetector.detect_cardinality_anomaly(1001, historical)
        assert not result.is_anomaly

    def test_cardinality_drop(self):
        historical = [1000, 1005, 998, 1002, 999, 1001, 1003, 997, 1004, 1000, 1002, 998, 1001, 999]
        result = AnomalyDetector.detect_cardinality_anomaly(500, historical)
        assert result.is_anomaly
