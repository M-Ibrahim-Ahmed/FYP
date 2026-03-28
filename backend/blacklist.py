# blacklist.py — ScamShield Blacklist Checker
# Checks URLs against known phishing/malicious domain blacklists.

import os
import csv
import re
from urllib.parse import urlparse


# Domains that should NEVER be blacklisted even if they appear in phishing URL datasets
# (because phishing URLs often mimic these domains in their paths)
TRUSTED_DOMAINS = {
    'google.com', 'www.google.com', 'accounts.google.com', 'docs.google.com',
    'youtube.com', 'www.youtube.com',
    'facebook.com', 'www.facebook.com',
    'twitter.com', 'www.twitter.com', 'x.com',
    'instagram.com', 'www.instagram.com',
    'linkedin.com', 'www.linkedin.com',
    'github.com', 'www.github.com',
    'microsoft.com', 'www.microsoft.com', 'login.microsoftonline.com',
    'apple.com', 'www.apple.com',
    'amazon.com', 'www.amazon.com',
    'paypal.com', 'www.paypal.com',
    'netflix.com', 'www.netflix.com',
    'wikipedia.org', 'en.wikipedia.org',
    'reddit.com', 'www.reddit.com',
    'yahoo.com', 'www.yahoo.com', 'mail.yahoo.com',
    'bing.com', 'www.bing.com',
    'whatsapp.com', 'www.whatsapp.com',
    'zoom.us', 'dropbox.com', 'www.dropbox.com',
    'stackoverflow.com', 'www.stackoverflow.com',
    'medium.com', 'cloudflare.com',
    'mozilla.org', 'www.mozilla.org',
}


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
        """Load blacklisted domains/URLs from a CSV file.
        
        Supports two CSV formats:
        1. Two-column CSV with 'url' and 'label' columns (label=1 means phishing)
        2. Single-column CSV with one URL/domain per row
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Read header row

                # Detect format: does the header have a 'label' column?
                has_label_col = False
                url_col_idx = 0
                label_col_idx = 1

                if header:
                    header_lower = [h.strip().lower() for h in header]
                    if 'label' in header_lower:
                        has_label_col = True
                        label_col_idx = header_lower.index('label')
                    if 'url' in header_lower:
                        url_col_idx = header_lower.index('url')

                count = 0
                for row in reader:
                    if not row:
                        continue

                    # If CSV has a label column, only include phishing URLs (label=1)
                    if has_label_col:
                        try:
                            label = int(row[label_col_idx].strip())
                            if label != 1:
                                continue  # Skip benign URLs (label=0)
                        except (IndexError, ValueError):
                            continue

                    entry = row[url_col_idx].strip().lower()
                    if not entry or entry.startswith('#'):
                        continue

                    # If it looks like a full URL
                    if entry.startswith('http://') or entry.startswith('https://'):
                        self.blacklisted_urls.add(entry.rstrip('/'))
                        try:
                            parsed = urlparse(entry)
                            hostname = parsed.hostname
                            # Don't blacklist well-known trusted domains
                            if hostname and hostname not in TRUSTED_DOMAINS:
                                self.blacklisted_domains.add(hostname)
                        except Exception:
                            pass
                    else:
                        # Treat as domain or bare URL — extract domain
                        domain = entry.split('/')[0]  # Take just the domain part
                        # Don't blacklist well-known trusted domains
                        if domain not in TRUSTED_DOMAINS:
                            self.blacklisted_domains.add(domain)

                    count += 1

            print(f'[ScamShield] Loaded {count} phishing entries '
                  f'({len(self.blacklisted_domains)} domains, '
                  f'{len(self.blacklisted_urls)} URLs) from {os.path.basename(filepath)}')
        except Exception as e:
            print(f'[ScamShield] Error loading blacklist: {e}')
            self._load_defaults()

    def _load_defaults(self):
        """Load a built-in set of known phishing/malicious patterns."""
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

        url_lower = url.lower().strip().rstrip('/')

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
        # (Only check against domains shorter than the target to avoid false positives)
        for bl_domain in self.blacklisted_domains:
            if domain.endswith('.' + bl_domain):
                return {
                    'is_blacklisted': True,
                    'matched': bl_domain,
                    'type': 'subdomain',
                }

        return {'is_blacklisted': False, 'matched': None, 'type': None}

    def check_urls(self, urls):
        """Check a list of URLs against the blacklist."""
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
