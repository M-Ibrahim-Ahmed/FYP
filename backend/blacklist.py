# blacklist.py — ScamShield Blacklist Checker
# Checks URLs against known phishing/malicious domain blacklists.

import os
import csv
import re
from urllib.parse import urlparse


class BlacklistChecker:
    """Checks URLs against a local blacklist of known malicious domains."""

    def __init__(self, blacklist_path=None):
        self.blacklisted_domains = set()
        self.blacklisted_urls = set()

        # Try to load from CSV file
        if blacklist_path and os.path.exists(blacklist_path):
            self._load_from_csv(blacklist_path)
        else:
            # Use built-in default blacklist
            self._load_defaults()

    def _load_from_csv(self, filepath):
        """Load blacklisted domains/URLs from a CSV file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    entry = row[0].strip().lower()
                    if not entry or entry.startswith('#'):
                        continue
                    # If it looks like a full URL
                    if entry.startswith('http://') or entry.startswith('https://'):
                        self.blacklisted_urls.add(entry)
                        try:
                            parsed = urlparse(entry)
                            if parsed.hostname:
                                self.blacklisted_domains.add(parsed.hostname)
                        except Exception:
                            pass
                    else:
                        # Treat as domain
                        self.blacklisted_domains.add(entry)
            print(f'[ScamShield] Loaded {len(self.blacklisted_domains)} blacklisted domains from {filepath}')
        except Exception as e:
            print(f'[ScamShield] Error loading blacklist: {e}')
            self._load_defaults()

    def _load_defaults(self):
        """Load a built-in set of known phishing/malicious patterns."""
        # Common phishing domain patterns (examples — extend as needed)
        default_domains = [
            'login-secure-update.com',
            'account-verify-now.com',
            'paypal-security-alert.com',
            'apple-id-verify.com',
            'microsoft-alert-center.com',
            'netflix-payment-update.com',
            'amazon-security-check.com',
            'bankofamerica-secure.com',
            'wellsfargo-online-update.com',
            'chase-account-verify.com',
            'google-docs-share.com',
            'facebook-security-team.com',
            'instagram-verify-badge.com',
            'twitter-support-help.com',
            'linkedin-login-secure.com',
            'account-verify-now.com',
        ]
        self.blacklisted_domains = set(default_domains)
        print(f'[ScamShield] Loaded {len(self.blacklisted_domains)} default blacklisted domains')

    def check_url(self, url):
        """Check if a URL or its domain is blacklisted.

        Returns:
            dict with 'is_blacklisted' (bool), 'matched' (str or None), 'type' (str)
        """
        if not url:
            return {'is_blacklisted': False, 'matched': None, 'type': None}

        url_lower = url.lower().strip()

        # Check exact URL match
        if url_lower in self.blacklisted_urls:
            return {
                'is_blacklisted': True,
                'matched': url_lower,
                'type': 'exact_url',
            }

        # Check domain match
        try:
            parsed = urlparse(url_lower)
            domain = parsed.hostname or ''
        except Exception:
            domain = ''

        if domain in self.blacklisted_domains:
            return {
                'is_blacklisted': True,
                'matched': domain,
                'type': 'domain',
            }

        # Check if domain is a subdomain of a blacklisted domain
        for bl_domain in self.blacklisted_domains:
            if domain.endswith('.' + bl_domain):
                return {
                    'is_blacklisted': True,
                    'matched': bl_domain,
                    'type': 'subdomain',
                }

        return {'is_blacklisted': False, 'matched': None, 'type': None}

    def check_urls(self, urls):
        """Check a list of URLs against the blacklist.

        Returns:
            list of check results
        """
        return [self.check_url(url) for url in urls]

    def add_domain(self, domain):
        """Dynamically add a domain to the blacklist."""
        self.blacklisted_domains.add(domain.lower().strip())

    def add_url(self, url):
        """Dynamically add a URL to the blacklist."""
        self.blacklisted_urls.add(url.lower().strip())

    @property
    def size(self):
        return len(self.blacklisted_domains) + len(self.blacklisted_urls)
