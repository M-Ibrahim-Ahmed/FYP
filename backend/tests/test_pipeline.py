"""Tests for the full ScamShield detection pipeline.

End-to-end tests: raw URL → heuristic analysis → ML prediction → blacklist check → final classification.
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestFullPipelineSafePage:
    """Test pipeline with a page containing only safe links."""

    def test_safe_page_overall_risk(self, client):
        safe_page = {
            'pageUrl': 'https://www.wikipedia.org',
            'pageTitle': 'Wikipedia',
            'timestamp': '2026-01-01T00:00:00Z',
            'links': [
                {'href': 'https://www.google.com/', 'text': 'Google', 'external': True, 'navigation': False},
                {'href': 'https://www.youtube.com/', 'text': 'YouTube', 'external': True, 'navigation': False},
                {'href': 'https://github.com/', 'text': 'GitHub', 'external': True, 'navigation': False},
            ],
            'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
        }
        response = client.post('/analyze', data=json.dumps(safe_page), content_type='application/json')
        data = response.get_json()
        assert data['summary']['overall_risk'] == 'safe'
        assert data['summary']['malicious'] == 0

    def test_safe_links_individually(self, client):
        safe_urls = ['https://www.google.com/', 'https://github.com/', 'https://www.amazon.com/']
        for url in safe_urls:
            response = client.post('/check', data=json.dumps({'url': url}), content_type='application/json')
            data = response.get_json()
            assert data['classification'] == 'safe', f'{url} should be safe, got {data["classification"]}'


class TestFullPipelineMaliciousPage:
    """Test pipeline with a page full of phishing links."""

    def test_malicious_page_flagged(self, client, malicious_page_data):
        response = client.post('/analyze', data=json.dumps(malicious_page_data), content_type='application/json')
        data = response.get_json()
        # Page with all phishing links + hidden iframe should be flagged
        assert data['summary']['overall_risk'] in ('suspicious', 'malicious')
        assert data['summary']['risk_score'] > 10

    def test_phishing_urls_individually(self, client, phishing_urls):
        for url in phishing_urls:
            response = client.post('/check', data=json.dumps({'url': url}), content_type='application/json')
            data = response.get_json()
            assert data['classification'] in ('suspicious', 'malicious'), \
                f'{url} should be suspicious/malicious, got {data["classification"]}'
            assert data['risk_score'] > 15


class TestFullPipelineMixedPage:
    """Test pipeline with a mix of safe and suspicious links."""

    def test_mixed_page_summary(self, client, sample_page_data):
        response = client.post('/analyze', data=json.dumps(sample_page_data), content_type='application/json')
        data = response.get_json()
        summary = data['summary']
        # Should have both safe and non-safe items
        assert summary['safe'] >= 1, 'Should have at least 1 safe item'
        assert summary['total_urls'] >= 2


class TestBlendedScoring:
    """Test the 60/40 heuristic/ML blended scoring."""

    def test_blended_score_present(self, client):
        """External URLs should have blended scoring applied."""
        response = client.post(
            '/check',
            data=json.dumps({'url': 'http://sketchy-looking-site.xyz/login'}),
            content_type='application/json',
        )
        data = response.get_json()
        # Should have ML data and blended scores
        if data.get('ml', {}).get('ml_available'):
            assert 'heuristic_score' in data or 'ml_score' in data or 'whitelisted' in data

    def test_risk_score_bounded(self, client, phishing_urls):
        """Risk scores should always be 0-100."""
        for url in phishing_urls:
            response = client.post('/check', data=json.dumps({'url': url}), content_type='application/json')
            data = response.get_json()
            assert 0 <= data['risk_score'] <= 100, f'Score {data["risk_score"]} out of bounds for {url}'


class TestWhitelistOverride:
    """Test that trusted domains bypass ML false positives."""

    def test_trusted_domains_always_safe(self, client, safe_urls):
        """Trusted domains should be classified safe even if ML might flag them."""
        for url in safe_urls:
            response = client.post('/check', data=json.dumps({'url': url}), content_type='application/json')
            data = response.get_json()
            assert data['classification'] == 'safe', \
                f'Trusted domain {url} should be safe, got {data["classification"]} (score={data["risk_score"]})'

    def test_whitelist_flag_set(self, client):
        """Whitelisted URLs should have the whitelisted flag."""
        response = client.post(
            '/check',
            data=json.dumps({'url': 'https://www.google.com/'}),
            content_type='application/json',
        )
        data = response.get_json()
        # Google is trusted — should either be whitelisted or have very low score
        assert data['classification'] == 'safe'
        assert data['risk_score'] <= 10


class TestBlacklistIntegration:
    """Test blacklist check within the full pipeline."""

    def test_blacklisted_url_is_malicious(self, client):
        """A URL whose domain is in the default blacklist should be flagged."""
        response = client.post(
            '/check',
            data=json.dumps({'url': 'http://login-secure-update.com/verify'}),
            content_type='application/json',
        )
        data = response.get_json()
        # Should be flagged as at least suspicious (blacklist + heuristic + ML blending)
        assert data['classification'] in ('suspicious', 'malicious')
        assert data['risk_score'] > 20


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_page(self, client):
        empty_page = {
            'pageUrl': 'https://blank.org',
            'pageTitle': '',
            'links': [], 'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
        }
        response = client.post('/analyze', data=json.dumps(empty_page), content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['summary']['overall_risk'] == 'safe'
        assert data['summary']['total_urls'] == 0

    def test_navigation_links_excluded(self, client):
        page = {
            'pageUrl': 'https://www.google.com',
            'pageTitle': 'Google',
            'links': [
                {'href': 'https://accounts.google.com', 'text': 'Sign in',
                 'external': False, 'navigation': True},
                {'href': 'https://maps.google.com', 'text': 'Maps',
                 'external': False, 'navigation': True},
            ],
            'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
        }
        response = client.post('/analyze', data=json.dumps(page), content_type='application/json')
        data = response.get_json()
        # Navigation links should be auto-safe
        for link in data['links']:
            assert link['classification'] == 'safe'
