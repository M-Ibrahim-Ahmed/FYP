# analyzer.py — ScamShield Heuristic URL Analyzer
# Analyzes URLs using multiple heuristic features to classify them as safe, suspicious, or malicious.

import math
import re
from urllib.parse import urlparse, parse_qs
from collections import Counter


# ─── Suspicious keyword lists ───
SUSPICIOUS_KEYWORDS = [
    'login', 'signin', 'verify', 'secure', 'account', 'update', 'confirm',
    'banking', 'password', 'credential', 'suspend', 'restrict', 'alert',
    'notification', 'expire', 'urgent', 'immediately', 'paypal', 'ebay',
    'amazon', 'apple', 'microsoft', 'google', 'facebook', 'netflix',
    'support', 'helpdesk', 'wallet', 'crypto', 'bitcoin', 'free', 'winner',
    'prize', 'congratulations', 'lucky', 'offer', 'discount', 'click',
    'limited', 'act-now', 'risk', 'unauthorized',
]

SUSPICIOUS_TLDS = [
    '.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.pw', '.cc',
    '.club', '.work', '.buzz', '.surf', '.icu', '.cam', '.bid',
    '.stream', '.racing', '.download', '.win', '.review', '.loan',
]

TRUSTED_DOMAINS = [
    'google.com', 'youtube.com', 'facebook.com', 'twitter.com', 'x.com',
    'instagram.com', 'linkedin.com', 'github.com', 'stackoverflow.com',
    'microsoft.com', 'apple.com', 'amazon.com', 'wikipedia.org',
    'reddit.com', 'netflix.com', 'whatsapp.com', 'yahoo.com',
    'bing.com', 'zoom.us', 'dropbox.com', 'medium.com',
    'cloudflare.com', 'mozilla.org', 'python.org', 'npmjs.com',
]


def extract_features(url):
    """Extract heuristic features from a URL for analysis."""
    features = {}

    try:
        parsed = urlparse(url)
    except Exception:
        return {'error': True, 'url': url}

    domain = parsed.hostname or ''
    path = parsed.path or ''
    query = parsed.query or ''
    full_url = url

    # ─── 1. URL Length ───
    features['url_length'] = len(full_url)
    features['domain_length'] = len(domain)
    features['path_length'] = len(path)

    # ─── 2. Dot count (subdomains indicator) ───
    features['dot_count'] = domain.count('.')
    features['subdomain_count'] = max(0, domain.count('.') - 1)

    # ─── 3. Special characters ───
    features['has_at_symbol'] = '@' in full_url
    features['has_double_slash_redirect'] = '//' in path
    features['hyphen_count'] = domain.count('-')
    features['underscore_count'] = full_url.count('_')
    features['digit_count_in_domain'] = sum(c.isdigit() for c in domain)
    features['special_char_count'] = sum(1 for c in full_url if c in '!#$%^&*()+=[]{}|;:<>?~')

    # ─── 4. HTTPS check ───
    features['uses_https'] = parsed.scheme == 'https'

    # ─── 5. IP address as domain ───
    features['has_ip_address'] = bool(re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain))

    # ─── 6. Domain entropy (randomness indicator) ───
    features['domain_entropy'] = _calculate_entropy(domain)

    # ─── 7. Suspicious keywords ───
    url_lower = full_url.lower()
    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in url_lower]
    features['suspicious_keyword_count'] = len(found_keywords)
    features['suspicious_keywords'] = found_keywords

    # ─── 8. Suspicious TLD ───
    features['has_suspicious_tld'] = any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS)

    # ─── 9. Trusted domain check ───
    features['is_trusted_domain'] = any(
        domain == td or domain.endswith('.' + td) for td in TRUSTED_DOMAINS
    )

    # ─── 10. URL shortener detection ───
    shorteners = ['bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 'is.gd',
                   'buff.ly', 'rebrand.ly', 'cutt.ly', 'shorturl.at']
    features['is_shortened'] = any(domain == s or domain.endswith('.' + s) for s in shorteners)

    # ─── 11. Query string analysis ───
    features['query_param_count'] = len(parse_qs(query))
    features['query_length'] = len(query)

    # ─── 12. Path depth ───
    features['path_depth'] = len([p for p in path.split('/') if p])

    # ─── 13. File extension in URL ───
    suspicious_extensions = ['.exe', '.zip', '.scr', '.bat', '.cmd', '.js', '.vbs', '.php']
    features['has_suspicious_extension'] = any(path.lower().endswith(ext) for ext in suspicious_extensions)

    # ─── 14. Port number in URL ───
    features['has_non_standard_port'] = parsed.port is not None and parsed.port not in [80, 443]

    return features


def calculate_risk_score(features):
    """Calculate a risk score (0-100) based on extracted features."""
    if features.get('error'):
        return 100  # Can't parse = maximum risk

    score = 0

    # Trusted domain gets a big safe bonus
    if features.get('is_trusted_domain'):
        return max(0, 5)  # Trusted domains are almost always safe

    # URL length penalties
    if features['url_length'] > 75:
        score += 8
    if features['url_length'] > 150:
        score += 12
    if features['url_length'] > 250:
        score += 10

    # Subdomain count
    if features['subdomain_count'] >= 3:
        score += 15
    elif features['subdomain_count'] >= 2:
        score += 8

    # Special characters
    if features['has_at_symbol']:
        score += 20
    if features['has_double_slash_redirect']:
        score += 15
    if features['hyphen_count'] >= 3:
        score += 10
    if features['digit_count_in_domain'] >= 4:
        score += 10

    # HTTPS
    if not features['uses_https']:
        score += 12

    # IP address as domain
    if features['has_ip_address']:
        score += 25

    # Domain entropy (high entropy = random-looking = suspicious)
    if features['domain_entropy'] > 3.5:
        score += 10
    if features['domain_entropy'] > 4.0:
        score += 10

    # Suspicious keywords
    keyword_count = features['suspicious_keyword_count']
    if keyword_count >= 3:
        score += 20
    elif keyword_count >= 1:
        score += 8

    # Suspicious TLD
    if features['has_suspicious_tld']:
        score += 15

    # URL shortener
    if features['is_shortened']:
        score += 10

    # Long query strings
    if features['query_length'] > 100:
        score += 8

    # Suspicious file extensions
    if features['has_suspicious_extension']:
        score += 15

    # Non-standard port
    if features['has_non_standard_port']:
        score += 12

    # Cap at 100
    return min(100, score)


def classify_url(url):
    """Classify a single URL and return the full analysis result."""
    features = extract_features(url)
    risk_score = calculate_risk_score(features)

    # Classification thresholds
    if risk_score <= 20:
        classification = 'safe'
    elif risk_score <= 55:
        classification = 'suspicious'
    else:
        classification = 'malicious'

    return {
        'url': url,
        'risk_score': risk_score,
        'classification': classification,
        'features': features,
    }


def analyze_page_data(page_data):
    """Analyze all URLs extracted from a page crawl."""
    results = {
        'page_url': page_data.get('pageUrl', ''),
        'page_title': page_data.get('pageTitle', ''),
        'timestamp': page_data.get('timestamp', ''),
        'summary': {
            'total_urls': 0,
            'safe': 0,
            'suspicious': 0,
            'malicious': 0,
            'overall_risk': 'safe',
            'risk_score': 0,
        },
        'links': [],
        'forms': [],
        'images': [],
        'redirects': [],
        'iframes': [],
    }

    all_scores = []

    # ─── Analyze links ───
    for link in page_data.get('links', []):
        analysis = classify_url(link.get('href', ''))
        analysis['text'] = link.get('text', '')
        analysis['target'] = link.get('target', '')
        results['links'].append(analysis)
        all_scores.append(analysis['risk_score'])

    # ─── Analyze forms ───
    for form in page_data.get('forms', []):
        analysis = classify_url(form.get('action', ''))
        analysis['method'] = form.get('method', 'GET')
        analysis['inputs'] = form.get('inputs', [])
        analysis['has_sensitive'] = form.get('hasSensitive', False)
        # Boost risk for forms collecting sensitive data over non-HTTPS
        if analysis['has_sensitive'] and not analysis['features'].get('uses_https'):
            analysis['risk_score'] = min(100, analysis['risk_score'] + 25)
            if analysis['risk_score'] > 55:
                analysis['classification'] = 'malicious'
            elif analysis['risk_score'] > 20:
                analysis['classification'] = 'suspicious'
        results['forms'].append(analysis)
        all_scores.append(analysis['risk_score'])

    # ─── Analyze clickable images ───
    for img in page_data.get('images', []):
        dest = img.get('destination')
        if dest:
            analysis = classify_url(dest)
            analysis['alt'] = img.get('alt', '')
            analysis['src'] = img.get('src', '')
            results['images'].append(analysis)
            all_scores.append(analysis['risk_score'])

    # ─── Analyze redirects ───
    for r in page_data.get('metaRedirects', []):
        analysis = classify_url(r.get('url', ''))
        analysis['redirect_type'] = 'meta-refresh'
        # Redirects are inherently more suspicious
        analysis['risk_score'] = min(100, analysis['risk_score'] + 10)
        if analysis['risk_score'] > 55:
            analysis['classification'] = 'malicious'
        elif analysis['risk_score'] > 20:
            analysis['classification'] = 'suspicious'
        results['redirects'].append(analysis)
        all_scores.append(analysis['risk_score'])

    for r in page_data.get('jsRedirects', []):
        analysis = classify_url(r.get('url', ''))
        analysis['redirect_type'] = 'javascript'
        analysis['risk_score'] = min(100, analysis['risk_score'] + 15)
        if analysis['risk_score'] > 55:
            analysis['classification'] = 'malicious'
        elif analysis['risk_score'] > 20:
            analysis['classification'] = 'suspicious'
        results['redirects'].append(analysis)
        all_scores.append(analysis['risk_score'])

    # ─── Analyze iframes ───
    for frame in page_data.get('iframes', []):
        analysis = classify_url(frame.get('src', ''))
        analysis['sandbox'] = frame.get('sandbox')
        analysis['hidden'] = frame.get('hidden', False)
        # Hidden iframes are very suspicious
        if analysis['hidden']:
            analysis['risk_score'] = min(100, analysis['risk_score'] + 30)
            if analysis['risk_score'] > 55:
                analysis['classification'] = 'malicious'
            elif analysis['risk_score'] > 20:
                analysis['classification'] = 'suspicious'
        results['iframes'].append(analysis)
        all_scores.append(analysis['risk_score'])

    # ─── Summary ───
    total = len(all_scores)
    results['summary']['total_urls'] = total
    results['summary']['safe'] = sum(1 for s in all_scores if s <= 20)
    results['summary']['suspicious'] = sum(1 for s in all_scores if 20 < s <= 55)
    results['summary']['malicious'] = sum(1 for s in all_scores if s > 55)

    if total > 0:
        avg_score = sum(all_scores) / total
        max_score = max(all_scores)
        # Overall risk weighted towards the worst URL found
        weighted = (avg_score * 0.4) + (max_score * 0.6)
        results['summary']['risk_score'] = round(weighted, 1)
        if weighted > 55:
            results['summary']['overall_risk'] = 'malicious'
        elif weighted > 20:
            results['summary']['overall_risk'] = 'suspicious'
        else:
            results['summary']['overall_risk'] = 'safe'
    else:
        results['summary']['risk_score'] = 0
        results['summary']['overall_risk'] = 'safe'

    return results


def _calculate_entropy(text):
    """Calculate Shannon entropy of a string."""
    if not text:
        return 0
    freq = Counter(text)
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())
