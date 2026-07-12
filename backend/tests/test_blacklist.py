"""Tests for blacklist.py — Blacklist URL checking."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blacklist import BlacklistChecker, TRUSTED_DOMAINS


class TestBlacklistChecker:
    """Test blacklist matching logic."""

    def test_default_blacklist_loads(self):
        checker = BlacklistChecker()  # No CSV, uses defaults
        assert checker.size > 0

    def test_known_phishing_domain(self):
        checker = BlacklistChecker()
        result = checker.check_url('http://login-secure-update.com/verify')
        assert result['is_blacklisted'] is True
        assert result['type'] == 'domain'

    def test_safe_domain_not_blacklisted(self):
        checker = BlacklistChecker()
        result = checker.check_url('https://www.google.com/')
        assert result['is_blacklisted'] is False

    def test_subdomain_of_blacklisted(self):
        checker = BlacklistChecker()
        result = checker.check_url('http://mail.login-secure-update.com/verify')
        assert result['is_blacklisted'] is True
        assert result['type'] == 'subdomain'

    def test_empty_url(self):
        checker = BlacklistChecker()
        result = checker.check_url('')
        assert result['is_blacklisted'] is False

    def test_none_url(self):
        checker = BlacklistChecker()
        result = checker.check_url(None)
        assert result['is_blacklisted'] is False

    def test_add_domain_dynamically(self):
        checker = BlacklistChecker()
        checker.add_domain('new-evil-domain.com')
        result = checker.check_url('http://new-evil-domain.com/phish')
        assert result['is_blacklisted'] is True

    def test_add_url_dynamically(self):
        checker = BlacklistChecker()
        checker.add_url('http://specific-phishing-page.com/login')
        result = checker.check_url('http://specific-phishing-page.com/login')
        assert result['is_blacklisted'] is True

    def test_check_urls_batch(self):
        checker = BlacklistChecker()
        results = checker.check_urls([
            'https://www.google.com/',
            'http://login-secure-update.com/',
        ])
        assert len(results) == 2
        assert results[0]['is_blacklisted'] is False
        assert results[1]['is_blacklisted'] is True

    def test_case_insensitive(self):
        checker = BlacklistChecker()
        result = checker.check_url('HTTP://LOGIN-SECURE-UPDATE.COM/verify')
        assert result['is_blacklisted'] is True

    def test_result_structure(self):
        checker = BlacklistChecker()
        result = checker.check_url('https://example.com/')
        assert 'is_blacklisted' in result
        assert 'matched' in result
        assert 'type' in result

    def test_trusted_domains_never_blacklisted(self):
        """Trusted domains in TRUSTED_DOMAINS set should never be blacklisted,
        even if someone adds them."""
        for domain in list(TRUSTED_DOMAINS)[:5]:
            checker = BlacklistChecker()
            result = checker.check_url(f'https://{domain}/')
            assert result['is_blacklisted'] is False, f'{domain} should never be blacklisted'


class TestBlacklistCSVLoading:
    """Test CSV loading functionality."""

    def test_csv_loading_from_actual_file(self):
        csv_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'blacklist_dataset_cleaned (2).csv'
        )
        if not os.path.exists(csv_path):
            import pytest
            pytest.skip('Blacklist CSV not found')

        checker = BlacklistChecker(csv_path)
        assert checker.size > 100, 'Should load a substantial number of entries from CSV'

    def test_nonexistent_csv_falls_back(self):
        checker = BlacklistChecker('/nonexistent/path/file.csv')
        # Should fall back to defaults without crashing
        assert checker.size > 0

    def test_size_property(self):
        checker = BlacklistChecker()
        assert isinstance(checker.size, int)
        assert checker.size == len(checker.blacklisted_domains) + len(checker.blacklisted_urls)
