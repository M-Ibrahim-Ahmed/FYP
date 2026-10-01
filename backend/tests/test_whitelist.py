"""Test: verify whitelist + new thresholds reduce false positives."""
from app import apply_ml_and_blacklist
from analyzer import classify_url

urls = [
    # Should be SAFE (trusted domains)
    'https://resources.github.com/',
    'https://services.github.com/',
    'https://www.youtube.com/watch?v=123',
    'https://docs.microsoft.com/en-us/',
    'https://www.instagram.com/github',
    # Should be SAFE (normal sites, not in whitelist but not phishing)
    'https://www.github.careers/careers-home',
    'https://www.kaggle.com/datasets',
    'https://checkphish.bolster.ai/',
    'https://www.phishtank.com/',
    # Should be SUSPICIOUS or MALICIOUS (real phishing patterns)
    'https://suspicious-phish-login.tk/verify',
    'http://192.168.1.1/paypal-login/secure/account',
    'http://update-your-bank-account-now.xyz/login.php',
]

print("=" * 75)
print("  URL Classification Test (new thresholds)")
print("=" * 75)
for url in urls:
    item = classify_url(url)
    result = apply_ml_and_blacklist(item)
    wl = ' [WL]' if result.get('whitelisted') else ''
    cls = result['classification']
    score = result['risk_score']
    h = result.get('heuristic_score', score)
    m = result.get('ml_score', '---')
    print(f"  {cls:>12} ({score:5.1f})  h={h:<5} ml={str(m):<6}  {url[:50]}{wl}")
print("=" * 75)
