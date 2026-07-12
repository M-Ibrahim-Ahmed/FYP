"""Tests for analyzer.py — Heuristic URL analysis."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analyzer import extract_features, calculate_risk_score, classify_url, analyze_page_data, _calculate_entropy


class TestExtractFeatures:
    """Test feature extraction from URLs."""

    def test_basic_safe_url(self):
        features = extract_features('https://www.google.com/')
        assert features['uses_https'] is True
        assert features['has_ip_address'] is False
        assert features['is_trusted_domain'] is True
        assert features['has_suspicious_tld'] is False
        # Note: 'google' matches the suspicious keyword list (designed to catch
        # phishing URLs impersonating Google), but the trusted domain flag
        # ensures risk score stays low regardless.

    def test_ip_address_url(self):
        features = extract_features('http://192.168.1.1/paypal-login/secure')
        assert features['has_ip_address'] is True
        assert features['uses_https'] is False

    def test_suspicious_tld(self):
        features = extract_features('http://evil-site.tk/login')
        assert features['has_suspicious_tld'] is True

    def test_suspicious_keywords(self):
        features = extract_features('http://example.com/login/verify/password/secure')
        assert features['suspicious_keyword_count'] >= 3
        assert 'login' in features['suspicious_keywords']
        assert 'verify' in features['suspicious_keywords']

    def test_subdomain_count(self):
        features = extract_features('http://a.b.c.d.example.com/page')
        assert features['subdomain_count'] >= 3

    def test_url_shortener_detection(self):
        features = extract_features('https://bit.ly/abc123')
        assert features['is_shortened'] is True

    def test_suspicious_extension(self):
        features = extract_features('http://example.com/download/file.exe')
        assert features['has_suspicious_extension'] is True

    def test_at_symbol(self):
        features = extract_features('http://user@evil.com/page')
        assert features['has_at_symbol'] is True

    def test_long_url(self):
        long_url = 'https://example.com/' + 'a' * 300
        features = extract_features(long_url)
        assert features['url_length'] > 250

    def test_query_params(self):
        features = extract_features('https://example.com/page?id=1&name=test&ref=abc')
        assert features['query_param_count'] == 3


class TestCalculateRiskScore:
    """Test risk score calculation."""

    def test_trusted_domain_low_score(self):
        features = extract_features('https://www.google.com/')
        score = calculate_risk_score(features)
        assert score <= 5, f'Trusted domain score should be <= 5, got {score}'

    def test_phishing_url_high_score(self):
        features = extract_features('http://192.168.1.1/paypal-login/verify/secure/account')
        score = calculate_risk_score(features)
        assert score > 50, f'Phishing URL score should be > 50, got {score}'

    def test_suspicious_tld_adds_score(self):
        features = extract_features('http://random-site.tk/')
        score = calculate_risk_score(features)
        # .tk TLD + no HTTPS should add risk
        assert score > 20

    def test_max_score_cap(self):
        """Score should never exceed 100."""
        features = extract_features(
            'http://192.168.1.1/login/verify/secure/password/account/update.exe?q=' + 'x' * 200
        )
        score = calculate_risk_score(features)
        assert score <= 100

    def test_error_features_max_score(self):
        score = calculate_risk_score({'error': True})
        assert score == 100


class TestClassifyUrl:
    """Test URL classification."""

    def test_safe_classification(self, safe_urls):
        for url in safe_urls:
            result = classify_url(url)
            assert result['classification'] == 'safe', f'{url} should be safe, got {result["classification"]}'
            assert result['risk_score'] <= 20

    def test_malicious_classification(self):
        result = classify_url('http://192.168.1.1/paypal-login/verify/secure/account')
        assert result['classification'] in ('suspicious', 'malicious')
        assert result['risk_score'] > 20

    def test_result_structure(self):
        result = classify_url('https://example.com/')
        assert 'url' in result
        assert 'risk_score' in result
        assert 'classification' in result
        assert 'features' in result
        assert result['classification'] in ('safe', 'suspicious', 'malicious')


class TestAnalyzePageData:
    """Test full page analysis."""

    def test_analyze_with_mixed_links(self, sample_page_data):
        results = analyze_page_data(sample_page_data)
        assert 'summary' in results
        assert 'links' in results
        assert results['summary']['total_urls'] > 0
        assert results['summary']['overall_risk'] in ('safe', 'suspicious', 'malicious')

    def test_analyze_empty_page(self):
        empty = {
            'pageUrl': 'https://example.com',
            'pageTitle': 'Empty',
            'links': [], 'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
        }
        results = analyze_page_data(empty)
        assert results['summary']['total_urls'] == 0
        assert results['summary']['overall_risk'] == 'safe'
        assert results['summary']['risk_score'] == 0

    def test_navigation_links_classified_safe(self):
        data = {
            'pageUrl': 'https://www.google.com',
            'pageTitle': 'Google',
            'links': [
                {'href': 'https://www.google.com/settings', 'text': 'Settings',
                 'external': False, 'navigation': True},
            ],
            'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
        }
        results = analyze_page_data(data)
        assert results['links'][0]['classification'] == 'safe'
        assert results['links'][0]['risk_score'] == 0

    def test_hidden_iframe_high_risk(self):
        data = {
            'pageUrl': 'https://example.com',
            'pageTitle': 'Test',
            'links': [], 'forms': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [],
            'iframes': [
                {'src': 'http://tracker.xyz/collect', 'sandbox': None, 'hidden': True},
            ],
        }
        results = analyze_page_data(data)
        iframe = results['iframes'][0]
        assert iframe['risk_score'] > 20, 'Hidden iframe should have elevated risk'

    def test_sensitive_form_risk_boost(self):
        data = {
            'pageUrl': 'http://sketchy-site.com',
            'pageTitle': 'Login',
            'links': [], 'images': [],
            'metaRedirects': [], 'jsRedirects': [], 'iframes': [],
            'forms': [
                {
                    'action': 'http://sketchy-site.com/submit',
                    'method': 'POST',
                    'inputs': [{'type': 'password', 'name': 'pass'}],
                    'hasSensitive': True,
                },
            ],
        }
        results = analyze_page_data(data)
        form = results['forms'][0]
        # Sensitive form over non-HTTPS should get a risk boost
        assert form['risk_score'] > 20


class TestEntropy:
    """Test Shannon entropy calculation."""

    def test_empty_string(self):
        assert _calculate_entropy('') == 0

    def test_single_char(self):
        assert _calculate_entropy('aaaa') == 0.0

    def test_high_entropy(self):
        entropy = _calculate_entropy('abcdefghijklmnop')
        assert entropy > 3.0, 'Diverse string should have high entropy'

    def test_low_entropy(self):
        entropy = _calculate_entropy('aabb')
        assert entropy < 2.0
