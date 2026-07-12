"""Tests for ml_predictor.py — ML-based URL prediction."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ml_predictor import MLPredictor


# Use a module-level predictor to avoid reloading the model per test
_predictor = None


def get_predictor():
    global _predictor
    if _predictor is None:
        # Explicitly find the model file — check multiple locations
        candidates = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'rf_phishing_model.pkl'),
            os.path.join(os.path.dirname(__file__), '..', 'rf_phishing_model.pkl'),
            os.path.join(os.getcwd(), 'rf_phishing_model.pkl'),
        ]
        model_path = next((p for p in candidates if os.path.exists(p)), None)
        _predictor = MLPredictor(model_path=model_path)
    return _predictor


class TestFeatureExtraction:
    """Test the 16-feature extraction pipeline."""

    def test_feature_count(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('https://www.google.com/')
        assert len(features) == 16, f'Expected 16 features, got {len(features)}'

    def test_feature_count_complex_url(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features(
            'http://192.168.1.1/paypal-login/verify?id=123&ref=abc'
        )
        assert len(features) == 16

    def test_url_length_feature(self):
        predictor = get_predictor()
        url = 'https://www.google.com/'
        features = predictor.extract_ml_features(url)
        assert features[0] == len(url), 'Feature 0 should be url_length'

    def test_ip_address_feature(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('http://192.168.1.1/page')
        assert features[1] == 1, 'Feature 1 should be 1 for IP address'

    def test_no_ip_address_feature(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('https://www.google.com/')
        assert features[1] == 0, 'Feature 1 should be 0 for domain name'

    def test_https_flag(self):
        predictor = get_predictor()
        features_https = predictor.extract_ml_features('https://example.com/')
        features_http = predictor.extract_ml_features('http://example.com/')
        assert features_https[3] == 1, 'HTTPS should be 1'
        assert features_http[3] == 0, 'HTTP should be 0'

    def test_hyphen_in_domain(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('http://my-evil-site.com/')
        assert features[10] == 1, 'Feature 10 should be 1 for hyphen in domain'

    def test_path_length_feature(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('https://example.com/very/long/path/here')
        assert features[9] == len('/very/long/path/here')

    def test_suspicious_extension_feature(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('http://example.com/download.exe')
        assert features[13] == 1, 'Feature 13 should be 1 for .exe extension'

    def test_invalid_url_returns_zeros(self):
        predictor = get_predictor()
        features = predictor.extract_ml_features('')
        assert len(features) == 16
        # Should not crash, returns zeros


class TestMLPrediction:
    """Test ML model predictions."""

    def test_model_loaded(self):
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available (rf_phishing_model.pkl not found)')
        assert predictor.available is True

    def test_predict_safe_url(self):
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available')

        result = predictor.predict('https://www.google.com/')
        assert result['ml_available'] is True
        assert result['ml_prediction'] == 'safe'
        assert result['ml_confidence'] > 0.5

    def test_predict_phishing_url(self):
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available')

        result = predictor.predict('http://192.168.1.1/paypal-login/secure/account')
        assert result['ml_available'] is True
        assert result['ml_prediction'] == 'malicious'

    def test_predict_result_structure(self):
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available')

        result = predictor.predict('https://example.com/')
        assert 'ml_available' in result
        assert 'ml_prediction' in result
        assert 'ml_confidence' in result
        assert 'ml_phishing_probability' in result
        assert result['ml_prediction'] in ('safe', 'malicious')
        assert 0 <= result['ml_confidence'] <= 1
        assert 0 <= result['ml_phishing_probability'] <= 1

    def test_predict_returns_features(self):
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available')

        result = predictor.predict('https://example.com/')
        assert 'ml_features' in result
        assert len(result['ml_features']) == 16

    def test_batch_predictions_consistent(self):
        """Same URL should always return the same prediction."""
        predictor = get_predictor()
        if not predictor.available:
            import pytest
            pytest.skip('ML model not available')

        url = 'https://www.github.com/'
        results = [predictor.predict(url) for _ in range(5)]
        predictions = [r['ml_prediction'] for r in results]
        assert len(set(predictions)) == 1, 'Same URL should give consistent predictions'


class TestMLGracefulDegradation:
    """Test behavior when model is not available."""

    def test_missing_model_file(self):
        predictor = MLPredictor(model_path='/nonexistent/model.pkl')
        assert predictor.available is False

    def test_predict_without_model(self):
        predictor = MLPredictor(model_path='/nonexistent/model.pkl')
        result = predictor.predict('https://example.com/')
        assert result['ml_available'] is False
        assert result['ml_prediction'] is None
        assert result['ml_confidence'] == 0


class TestShannonEntropy:
    """Test the static entropy calculation."""

    def test_empty_string(self):
        assert MLPredictor._shannon_entropy('') == 0.0

    def test_uniform_string(self):
        assert MLPredictor._shannon_entropy('aaaa') == 0.0

    def test_max_entropy_two_chars(self):
        # Equal distribution of 2 chars = 1 bit
        entropy = MLPredictor._shannon_entropy('ab')
        assert abs(entropy - 1.0) < 0.01

    def test_higher_entropy_for_diverse_strings(self):
        low = MLPredictor._shannon_entropy('aabb')
        high = MLPredictor._shannon_entropy('abcdefgh')
        assert high > low
