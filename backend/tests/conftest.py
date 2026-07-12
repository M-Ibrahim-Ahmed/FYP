"""Shared pytest fixtures for ScamShield backend tests."""

import sys
import os

# Ensure backend directory is importable
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Prevent dotenv from loading real credentials during tests
os.environ.setdefault('MONGO_URI', '')
os.environ.setdefault('SELENIUM_REMOTE_URL', '')

import pytest


@pytest.fixture
def app():
    """Create a Flask test app with test config."""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client — no real server needed."""
    return app.test_client()


@pytest.fixture
def safe_urls():
    """Known safe URLs for testing."""
    return [
        'https://www.google.com/',
        'https://github.com/trending',
        'https://www.youtube.com/watch?v=abc123',
        'https://stackoverflow.com/questions',
        'https://www.wikipedia.org/',
        'https://www.amazon.com/',
        'https://www.netflix.com/',
    ]


@pytest.fixture
def phishing_urls():
    """Known phishing-pattern URLs for testing."""
    return [
        'http://192.168.1.1/paypal-login/secure/account',
        'http://update-your-bank-account-now.xyz/login.php',
        'http://free-prize-winner-2025.tk/claim',
        'http://secure-verify-paypal.com.suspicious-domain.tk/login',
        'http://apple-id-verify-support.cf/signin',
    ]


@pytest.fixture
def sample_page_data():
    """Sample page crawl data mimicking what the content script sends."""
    return {
        'pageUrl': 'https://example.com',
        'pageTitle': 'Test Page',
        'timestamp': '2026-01-01T00:00:00Z',
        'links': [
            {
                'href': 'https://www.google.com/',
                'text': 'Google',
                'target': '_blank',
                'external': True,
                'navigation': False,
            },
            {
                'href': 'http://suspicious-login.tk/verify',
                'text': 'Click here',
                'target': '_blank',
                'external': True,
                'navigation': False,
            },
            {
                'href': 'https://example.com/about',
                'text': 'About',
                'target': '',
                'external': False,
                'navigation': False,
            },
        ],
        'forms': [
            {
                'action': 'https://example.com/login',
                'method': 'POST',
                'inputs': [{'type': 'text', 'name': 'username'}, {'type': 'password', 'name': 'password'}],
                'hasSensitive': True,
            },
        ],
        'images': [],
        'metaRedirects': [],
        'jsRedirects': [],
        'iframes': [],
    }


@pytest.fixture
def malicious_page_data():
    """Page data with many malicious indicators."""
    return {
        'pageUrl': 'http://fake-bank-login.tk',
        'pageTitle': 'Verify Your Account',
        'timestamp': '2026-01-01T00:00:00Z',
        'links': [
            {
                'href': 'http://192.168.1.1/paypal-login/secure/account',
                'text': 'Verify PayPal',
                'target': '_blank',
                'external': True,
                'navigation': False,
            },
            {
                'href': 'http://update-your-bank-account-now.xyz/login.php',
                'text': 'Update Bank',
                'target': '_blank',
                'external': True,
                'navigation': False,
            },
            {
                'href': 'http://free-prize-winner-2025.tk/claim',
                'text': 'Claim Prize',
                'target': '_blank',
                'external': True,
                'navigation': False,
            },
        ],
        'forms': [],
        'images': [],
        'metaRedirects': [],
        'jsRedirects': [],
        'iframes': [
            {
                'src': 'http://hidden-tracker.xyz/collect',
                'sandbox': None,
                'width': '0',
                'height': '0',
                'hidden': True,
            },
        ],
    }
