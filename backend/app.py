# app.py — ScamShield Flask Backend
# 3-stage pipeline: Blacklist -> Heuristics -> ML Model

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import glob

# Load environment variables from .env file
load_dotenv()

from analyzer import analyze_page_data, classify_url
from blacklist import BlacklistChecker
from ml_predictor import MLPredictor
from safe_preview import SafePreview

import time
import logging
from datetime import datetime
from collections import defaultdict

# ─── Logging setup ───
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('ScamShield')

app = Flask(__name__)
CORS(app)  # Allow requests from Chrome extension

# ─── Initialize components ───

# Blacklist: search multiple locations for the CSV
blacklist_csv = None
search_paths = [
    os.path.dirname(__file__),  # backend/
    os.path.join(os.path.dirname(__file__), '..'),  # project root
    os.path.join(os.path.dirname(__file__), '..', 'datasets'),  # project root/datasets
    os.getcwd(),
]
for search_dir in search_paths:
    candidates = glob.glob(os.path.join(search_dir, 'blacklist_dataset_cleaned*csv'))
    if candidates:
        blacklist_csv = candidates[0]
        break
blacklist = BlacklistChecker(blacklist_csv)

# ML Model: specify model path in models/ folder
model_path = None
model_search_paths = [
    os.path.join(os.path.dirname(__file__), '..', 'models', 'rf_phishing_model.pkl'),  # ../models/
    os.path.join(os.path.dirname(__file__), 'rf_phishing_model.pkl'),  # backend/
    os.path.join(os.getcwd(), 'models', 'rf_phishing_model.pkl'),  # cwd/models/
]
for path in model_search_paths:
    if os.path.exists(path):
        model_path = path
        break
ml_model = MLPredictor(model_path=model_path)

# Safe Preview service
preview_service = SafePreview()

# Simple in-memory storage for scan history (for demo purposes)
# In production, use a proper database
scan_history = []


def apply_ml_and_blacklist(item):
    """Apply ML prediction and blacklist check to a single analyzed item.
    Pipeline: Blacklist (highest priority) → ML → Heuristics (fallback).
    """
    # Skip ML/blacklist for same-site or navigation links (already classified safe)
    if not item.get('external', True) or item.get('navigation', False):
        return item

    url = item.get('url', '')

    # 1) Blacklist check (overrides everything)
    bl_result = blacklist.check_url(url)
    item['blacklisted'] = bl_result
    if bl_result['is_blacklisted']:
        item['classification'] = 'malicious'
        item['risk_score'] = 100
        logger.warning('  BLACKLISTED: %s (matched: %s)', url[:80], bl_result['matched'])
        return item

    # 2) Trusted domain override — if heuristic already identified this as a
    #    known-good domain (github.com, youtube.com, etc.), skip ML.
    #    The ML model doesn't know about domain reputation and would
    #    flag subdomains like resources.github.com due to URL structure.
    heuristic_score = item.get('risk_score', 0)
    is_trusted = item.get('features', {}).get('is_trusted_domain', False)

    if is_trusted and heuristic_score <= 5:
        item['classification'] = 'safe'
        item['risk_score'] = heuristic_score
        item['whitelisted'] = True
        logger.info('  [SAFE] %s | trusted domain (whitelist override)', url[:60])
        return item

    # 3) ML prediction (blended with heuristic score)
    ml_result = ml_model.predict(url)
    item['ml'] = ml_result

    if ml_result.get('ml_available'):
        phishing_prob = ml_result['ml_phishing_probability']

        # Convert ML probability to 0-100 score
        ml_score = phishing_prob * 100

        # Blend: 60% heuristic + 40% ML
        # Heuristic gets more weight because ML tends to over-flag normal subdomains
        blended_score = (heuristic_score * 0.6) + (ml_score * 0.4)
        item['risk_score'] = round(blended_score, 1)
        item['heuristic_score'] = heuristic_score
        item['ml_score'] = round(ml_score, 1)

        # Reclassify based on blended score
        # Higher thresholds to reduce false positives on legitimate sites
        if blended_score > 70:
            item['classification'] = 'malicious'
        elif blended_score > 35:
            item['classification'] = 'suspicious'
        else:
            item['classification'] = 'safe'

        logger.info('  [%s] %s | heuristic=%s ml=%.1f blended=%.1f',
                    item['classification'].upper(), url[:60],
                    heuristic_score, ml_score, blended_score)

    return item


def recalculate_summary(results):
    """Recalculate summary stats after ML and blacklist overlays."""
    all_items = []
    for category in ['links', 'forms', 'images', 'redirects', 'iframes']:
        all_items.extend(results.get(category, []))

    if all_items:
        results['summary']['safe'] = sum(1 for i in all_items if i['classification'] == 'safe')
        results['summary']['suspicious'] = sum(1 for i in all_items if i['classification'] == 'suspicious')
        results['summary']['malicious'] = sum(1 for i in all_items if i['classification'] == 'malicious')

        n_suspicious = results['summary']['suspicious']
        n_malicious = results['summary']['malicious']
        scores = [i['risk_score'] for i in all_items]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)

        # Page-level risk: mostly average, max only as a minor bump.
        # This prevents 1 borderline link from flagging an entire page.
        weighted = (avg_score * 0.7) + (max_score * 0.3)
        results['summary']['risk_score'] = round(weighted, 1)

        # Page-level classification — requires real threats, not just borderline links
        if n_malicious >= 2 or (n_malicious >= 1 and weighted > 60):
            results['summary']['overall_risk'] = 'malicious'
        elif n_malicious >= 1 or (n_suspicious >= 3 and weighted > 25) or weighted > 30:
            results['summary']['overall_risk'] = 'suspicious'
        else:
            results['summary']['overall_risk'] = 'safe'

    results['summary']['ml_enabled'] = ml_model.available
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'ScamShield Backend',
        'version': '1.0',
        'blacklist_size': blacklist.size,
        'ml_model_loaded': ml_model.available,
        'timestamp': time.time(),
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze page data: Blacklist -> Heuristics -> ML pipeline."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        page_url = data.get('pageUrl', 'unknown')
        logger.info('--- ANALYZE PAGE: %s ---', page_url[:80])
        start = time.time()

        # Stage 1: Heuristic analysis on all URLs
        results = analyze_page_data(data)

        # Stage 2 & 3: Apply ML + blacklist on each item
        total_urls = 0
        for category in ['links', 'forms', 'images', 'redirects', 'iframes']:
            items = results.get(category, [])
            results[category] = [apply_ml_and_blacklist(item) for item in items]
            total_urls += len(items)

        # Recalculate summary
        results = recalculate_summary(results)
        elapsed = round((time.time() - start) * 1000)

        summary = results['summary']
        logger.info('--- RESULT: %s | %d URLs analyzed in %dms | safe=%d suspicious=%d malicious=%d | risk_score=%.1f ---',
                    summary.get('overall_risk', '?').upper(), total_urls, elapsed,
                    summary.get('safe', 0), summary.get('suspicious', 0),
                    summary.get('malicious', 0), summary.get('risk_score', 0))

        # Store in history (keep last 100 scans)
        scan_record = {
            'page_url': page_url,
            'scanned_at': datetime.utcnow().isoformat(),
            'summary': summary,
            'total_urls': total_urls,
        }
        scan_history.insert(0, scan_record)
        if len(scan_history) > 100:
            scan_history.pop()

        return jsonify(results)
    except Exception as e:
        logger.error('Analyze error: %s', str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/check', methods=['POST'])
def check_single():
    """Check a single URL through the full 3-stage pipeline."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" field'}), 400

        url = data['url']
        logger.info('CHECK URL: %s', url[:80])

        # Heuristic analysis
        result = classify_url(url)

        # Apply ML + blacklist
        result = apply_ml_and_blacklist(result)

        logger.info('CHECK RESULT: %s | risk_score=%.1f',
                    result['classification'].upper(), result['risk_score'])

        return jsonify(result)
    except Exception as e:
        logger.error('Check error: %s', str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/preview', methods=['POST'])
def preview():
    """Safe preview of a suspicious URL (sandboxed screenshot)."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" field'}), 400

        url = data['url']
        timeout = data.get('timeout', 30)

        logger.info('PREVIEW REQUEST: %s', url[:80])
        result = preview_service.capture(url, timeout=timeout)

        if result['success']:
            logger.info('PREVIEW SUCCESS: %s (method: %s, load_time: %.2fs)',
                        url[:60], result.get('method', '?'), result.get('load_time', 0))
        else:
            logger.warning('PREVIEW FAILED: %s | error: %s',
                           url[:60], result.get('error', 'Unknown'))

        return jsonify(result)
    except Exception as e:
        logger.error('Preview error: %s', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Get aggregate statistics from scan history."""
    try:
        if not scan_history:
            return jsonify({
                'available': False,
                'total_scans': 0,
                'total_urls_analyzed': 0,
                'blacklisted_urls': 0,
                'classifications': {'safe': 0, 'suspicious': 0, 'malicious': 0},
            })

        total_scans = len(scan_history)
        total_urls = sum(s.get('total_urls', 0) for s in scan_history)

        classifications = defaultdict(int)
        for scan in scan_history:
            summary = scan.get('summary', {})
            classifications['safe'] += summary.get('safe', 0)
            classifications['suspicious'] += summary.get('suspicious', 0)
            classifications['malicious'] += summary.get('malicious', 0)

        # Approximate blacklisted count (we don't store detailed URL-level data in history)
        blacklisted_urls = classifications['malicious']  # rough estimate

        return jsonify({
            'available': True,
            'total_scans': total_scans,
            'total_urls_analyzed': total_urls,
            'blacklisted_urls': blacklisted_urls,
            'classifications': dict(classifications),
        })
    except Exception as e:
        logger.error('Stats error: %s', str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def history():
    """Get recent scan history."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        scans = scan_history[start_idx:end_idx]

        return jsonify({
            'scans': scans,
            'total': len(scan_history),
            'page': page,
            'per_page': per_page,
        })
    except Exception as e:
        logger.error('History error: %s', str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('=' * 55)
    print('  [*] ScamShield Backend Server')
    print('=' * 55)
    print(f'  ML Model:     {"[OK] Loaded" if ml_model.available else "[X] Not available"}')
    print(f'  Blacklist:    {blacklist.size} entries')
    print(f'  Preview:      {"[OK] Docker Selenium" if preview_service.is_docker_connected else "[OK] API fallback"}')
    print(f'  Server:       http://localhost:5000')
    print('=' * 55)
    app.run(host='0.0.0.0', port=5000, debug=True)
