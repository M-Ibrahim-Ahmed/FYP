"""Tests for app.py — Flask API endpoints."""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestHealthEndpoint:
    """Test GET /health."""

    def test_health_returns_200(self, client):
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        response = client.get('/health')
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['service'] == 'ScamShield Backend'
        assert 'ml_model_loaded' in data
        assert 'blacklist_size' in data
        assert 'database_connected' in data
        assert 'safe_preview_available' in data
        assert 'timestamp' in data

    def test_health_blacklist_loaded(self, client):
        response = client.get('/health')
        data = response.get_json()
        assert data['blacklist_size'] > 0


class TestAnalyzeEndpoint:
    """Test POST /analyze."""

    def test_analyze_valid_page(self, client, sample_page_data):
        response = client.post(
            '/analyze',
            data=json.dumps(sample_page_data),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'summary' in data
        assert 'links' in data
        assert data['summary']['overall_risk'] in ('safe', 'suspicious', 'malicious')

    def test_analyze_empty_body(self, client):
        response = client.post('/analyze', content_type='application/json')
        assert response.status_code in (400, 500), 'Empty body should be rejected'

    def test_analyze_returns_classifications(self, client, sample_page_data):
        response = client.post(
            '/analyze',
            data=json.dumps(sample_page_data),
            content_type='application/json',
        )
        data = response.get_json()
        for link in data.get('links', []):
            assert 'classification' in link
            assert 'risk_score' in link
            assert link['classification'] in ('safe', 'suspicious', 'malicious')

    def test_analyze_malicious_page(self, client, malicious_page_data):
        response = client.post(
            '/analyze',
            data=json.dumps(malicious_page_data),
            content_type='application/json',
        )
        data = response.get_json()
        summary = data['summary']
        # Page with all phishing links should not be "safe"
        assert summary['overall_risk'] in ('suspicious', 'malicious')
        assert summary['risk_score'] > 10

    def test_analyze_summary_counts(self, client, sample_page_data):
        response = client.post(
            '/analyze',
            data=json.dumps(sample_page_data),
            content_type='application/json',
        )
        data = response.get_json()
        summary = data['summary']
        total = summary.get('safe', 0) + summary.get('suspicious', 0) + summary.get('malicious', 0)
        assert total > 0


class TestCheckEndpoint:
    """Test POST /check."""

    def test_check_safe_url(self, client):
        response = client.post(
            '/check',
            data=json.dumps({'url': 'https://www.google.com/'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['classification'] == 'safe'

    def test_check_phishing_url(self, client):
        response = client.post(
            '/check',
            data=json.dumps({'url': 'http://192.168.1.1/paypal-login/secure/account'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['classification'] in ('suspicious', 'malicious')

    def test_check_missing_url(self, client):
        response = client.post(
            '/check',
            data=json.dumps({}),
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_check_result_structure(self, client):
        response = client.post(
            '/check',
            data=json.dumps({'url': 'https://example.com/'}),
            content_type='application/json',
        )
        data = response.get_json()
        assert 'url' in data
        assert 'classification' in data
        assert 'risk_score' in data

    def test_check_includes_ml_data(self, client):
        response = client.post(
            '/check',
            data=json.dumps({'url': 'https://example.com/'}),
            content_type='application/json',
        )
        data = response.get_json()
        # Should have ML and blacklist data
        assert 'ml' in data or 'whitelisted' in data
        assert 'blacklisted' in data


class TestPreviewEndpoint:
    """Test POST /preview."""

    def test_preview_missing_url(self, client):
        response = client.post(
            '/preview',
            data=json.dumps({}),
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_preview_invalid_url(self, client):
        response = client.post(
            '/preview',
            data=json.dumps({'url': 'not-a-url'}),
            content_type='application/json',
        )
        data = response.get_json()
        assert data.get('success') is False

    def test_preview_returns_result(self, client):
        """Preview endpoint should return a result dict (may fail if Docker not running)."""
        response = client.post(
            '/preview',
            data=json.dumps({'url': 'https://www.google.com/', 'timeout': 10}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        # Should have success field regardless of outcome
        assert 'success' in data


class TestHistoryEndpoint:
    """Test GET /history."""

    def test_history_returns_200(self, client):
        response = client.get('/history')
        assert response.status_code == 200

    def test_history_response_structure(self, client):
        response = client.get('/history')
        data = response.get_json()
        assert 'scans' in data
        assert 'total' in data
        assert 'page' in data


class TestStatsEndpoint:
    """Test GET /stats."""

    def test_stats_returns_200(self, client):
        response = client.get('/stats')
        assert response.status_code == 200

    def test_stats_response_structure(self, client):
        response = client.get('/stats')
        data = response.get_json()
        assert 'available' in data
