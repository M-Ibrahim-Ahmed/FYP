# app.py — ScamShield Flask Backend
# 3-stage pipeline: Blacklist -> Heuristics -> ML Model
# With MongoDB persistence, scan history, stats, and safe preview.

from flask import Flask, request, jsonify
from flask_cors import CORS
from analyzer import analyze_page_data, classify_url
from blacklist import BlacklistChecker
from ml_predictor import MLPredictor
from db import Database
from safe_preview import SafePreview
import os
import time
import logging
from datetime import datetime

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

# Blacklist: use the user-provided CSV in the extension root directory
blacklist_csv = os.path.join(os.path.dirname(__file__), '..', 'blacklist_dataset_cleaned (2).csv')
if not os.path.exists(blacklist_csv):
    # Fallback: check backend directory
    blacklist_csv = os.path.join(os.path.dirname(__file__), 'blacklist.csv')
blacklist = BlacklistChecker(blacklist_csv if os.path.exists(blacklist_csv) else None)

ml_model = MLPredictor()       # Loads rf_phishing_model.pkl automatically
db = Database()                # MongoDB connection (gracefully degrades)
safe_preview = SafePreview()   # Selenium screenshot service


def apply_ml_and_blacklist(item):
    """Apply ML prediction and blacklist check to a single analyzed item.
    Pipeline: Blacklist (highest priority) → ML → Heuristics (fallback).
    """
    # Skip ML/blacklist for same-site links (already classified safe by analyzer)
    if not item.get('external', True):
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

    # 2) ML prediction (blended with heuristic score)
    ml_result = ml_model.predict(url)
    item['ml'] = ml_result

    if ml_result.get('ml_available'):
        heuristic_score = item.get('risk_score', 0)
        phishing_prob = ml_result['ml_phishing_probability']

        # Convert ML probability to 0-100 score
        ml_score = phishing_prob * 100

        # Blend: 40% heuristic + 60% ML (ML gets more weight since it's trained)
        blended_score = (heuristic_score * 0.4) + (ml_score * 0.6)
        item['risk_score'] = round(blended_score, 1)
        item['heuristic_score'] = heuristic_score
        item['ml_score'] = round(ml_score, 1)

        # Reclassify based on blended score
        if blended_score > 55:
            item['classification'] = 'malicious'
        elif blended_score > 20:
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
        scores = [i['risk_score'] for i in all_items]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        weighted = (avg_score * 0.4) + (max_score * 0.6)
        results['summary']['risk_score'] = round(weighted, 1)
        if weighted > 55:
            results['summary']['overall_risk'] = 'malicious'
        elif weighted > 20:
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
        'database_connected': db.is_available,
        'safe_preview_available': safe_preview.is_available,
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

        # Persist to MongoDB (non-blocking — errors won't affect response)
        scan_id = db.save_scan(results)
        if scan_id:
            results['scan_id'] = scan_id

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


@app.route('/history', methods=['GET'])
def history():
    """Get paginated scan history from MongoDB."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # Cap at 100

        result = db.get_history(page=page, per_page=per_page)
        return jsonify(result)
    except Exception as e:
        logger.error('History error: %s', str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Get aggregate scan statistics from MongoDB."""
    try:
        result = db.get_stats()
        return jsonify(result)
    except Exception as e:
        logger.error('Stats error: %s', str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/preview', methods=['POST'])
def preview():
    """Capture a safe screenshot of a suspicious URL using the sandboxed browser."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" field'}), 400

        url = data['url']
        timeout = data.get('timeout', 15)
        logger.info('PREVIEW URL: %s', url[:80])

        result = safe_preview.capture(url, timeout=timeout)
        return jsonify(result)
    except Exception as e:
        logger.error('Preview error: %s', str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('=' * 55)
    print('  🛡️  ScamShield Backend Server')
    print('=' * 55)
    print(f'  ML Model:     {"✅ Loaded" if ml_model.available else "❌ Not available"}')
    print(f'  Blacklist:    {blacklist.size} entries')
    print(f'  Database:     {"✅ Connected" if db.is_available else "⚠️  Not connected (running without DB)"}')
    print(f'  Safe Preview: {"✅ Available" if safe_preview.is_available else "⚠️  Not available"}')
    print(f'  Server:       http://localhost:5000')
    print('=' * 55)
    app.run(host='0.0.0.0', port=5000, debug=True)
