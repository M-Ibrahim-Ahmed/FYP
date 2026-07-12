"""
benchmark.py - ScamShield Comprehensive Performance Benchmark
=============================================================
Generates all metrics requested by the FYP committee:
1. Accuracy, Precision, Recall, F1-Score (per class and overall)
2. Processing time per URL (ms)
3. CPU usage (%)
4. Memory usage (MB)
5. Model size and complexity stats
6. Confusion matrix analysis
7. Comparison table template (vs. base paper)
8. Real-world URL evaluation

Usage: python benchmark.py
Output: benchmark_results.txt + benchmark_results.csv
"""

import os
import sys
import time
import csv
import warnings
import tracemalloc
import psutil

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)
import joblib

warnings.filterwarnings('ignore')

# ─── Configuration ───
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'url_features_extracted1.csv')
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rf_phishing_model.pkl')
OUTPUT_TXT = os.path.join(os.path.dirname(__file__), 'benchmark_results.txt')
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), 'benchmark_results.csv')

FEATURE_COLUMNS = [
    'url_length', 'has_ip_address', 'dot_count', 'https_flag',
    'url_entropy', 'token_count', 'subdomain_count', 'query_param_count',
    'tld_length', 'path_length', 'has_hyphen_in_domain', 'number_of_digits',
    'tld_popularity', 'suspicious_file_extension', 'domain_name_length',
    'percentage_numeric_chars',
]
LABEL_COLUMN = 'ClassLabel'


# ─── Real-World Test URLs ───
REAL_WORLD_URLS = [
    # Known Safe
    ('https://www.google.com/', 'safe'),
    ('https://github.com/trending', 'safe'),
    ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'safe'),
    ('https://stackoverflow.com/questions', 'safe'),
    ('https://www.wikipedia.org/', 'safe'),
    ('https://www.amazon.com/', 'safe'),
    ('https://docs.python.org/3/', 'safe'),
    ('https://www.linkedin.com/feed/', 'safe'),
    ('https://www.reddit.com/', 'safe'),
    ('https://www.netflix.com/', 'safe'),
    # Known Phishing / Suspicious patterns
    ('http://192.168.1.1/paypal-login/secure/account', 'phishing'),
    ('http://update-your-bank-account-now.xyz/login.php', 'phishing'),
    ('http://free-prize-winner-2025.tk/claim', 'phishing'),
    ('http://secure-verify-paypal.com.suspicious-domain.tk/login', 'phishing'),
    ('http://apple-id-verify-support.cf/signin', 'phishing'),
    ('http://facebook-login-secure.gq/password-reset', 'phishing'),
    ('http://netflix-billing-update.ml/account/verify', 'phishing'),
    ('http://microsoft-alert-security.pw/urgent', 'phishing'),
    ('http://amazon-order-confirm.buzz/tracking?id=838291', 'phishing'),
    ('https://bit.ly/3xSu5pq', 'phishing'),
]


def section(title, f):
    """Print a formatted section header."""
    line = '=' * 65
    f.write(f'\n{line}\n  {title}\n{line}\n')
    print(f'\n{line}\n  {title}\n{line}')


def write(text, f):
    """Write to both console and file."""
    f.write(text + '\n')
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


def main():
    # Start memory tracking
    tracemalloc.start()
    process = psutil.Process(os.getpid())

    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:

        section('ScamShield - Performance Benchmark Report', f)
        write(f'  Date: {time.strftime("%Y-%m-%d %H:%M:%S")}', f)
        write(f'  System: {os.name} / Python {sys.version.split()[0]}', f)

        # ────────────────────────────────────────────
        # 1. Load Dataset
        # ────────────────────────────────────────────
        section('1. Dataset Overview', f)

        df = pd.read_csv(DATASET_PATH)
        df = df.dropna(subset=[LABEL_COLUMN])
        total = len(df)
        n_phishing = (df[LABEL_COLUMN] == 0).sum()
        n_benign = (df[LABEL_COLUMN] == 1).sum()

        write(f'  Dataset:          url_features_extracted1.csv', f)
        write(f'  Total Samples:    {total:,}', f)
        write(f'  Phishing (0):     {n_phishing:,} ({n_phishing/total*100:.1f}%)', f)
        write(f'  Benign (1):       {n_benign:,} ({n_benign/total*100:.1f}%)', f)
        write(f'  Features:         {len(FEATURE_COLUMNS)}', f)
        write(f'  Feature Names:    {", ".join(FEATURE_COLUMNS)}', f)

        # ────────────────────────────────────────────
        # 2. Load Model & Prepare Data
        # ────────────────────────────────────────────
        section('2. Model Information', f)

        model = joblib.load(MODEL_PATH)
        model_size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)

        write(f'  Algorithm:        Random Forest', f)
        write(f'  N Estimators:     {model.n_estimators}', f)
        write(f'  Max Depth:        {model.max_depth}', f)
        write(f'  Min Samples Split:{model.min_samples_split}', f)
        write(f'  Min Samples Leaf: {model.min_samples_leaf}', f)
        write(f'  Class Weight:     {model.class_weight}', f)
        write(f'  N Features:       {model.n_features_in_}', f)
        write(f'  Model Size:       {model_size_mb:.2f} MB', f)

        X = df[FEATURE_COLUMNS].fillna(0)
        y = df[LABEL_COLUMN].astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        write(f'  Train Set:        {len(X_train):,}', f)
        write(f'  Test Set:         {len(X_test):,}', f)

        # ────────────────────────────────────────────
        # 3. Classification Metrics
        # ────────────────────────────────────────────
        section('3. Classification Performance (Test Set)', f)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec_w = precision_score(y_test, y_pred, average='weighted')
        rec_w = recall_score(y_test, y_pred, average='weighted')
        f1_w = f1_score(y_test, y_pred, average='weighted')
        auc = roc_auc_score(y_test, y_proba[:, 1])

        # Per-class metrics
        prec_phish = precision_score(y_test, y_pred, pos_label=0)
        rec_phish = recall_score(y_test, y_pred, pos_label=0)
        f1_phish = f1_score(y_test, y_pred, pos_label=0)

        prec_benign = precision_score(y_test, y_pred, pos_label=1)
        rec_benign = recall_score(y_test, y_pred, pos_label=1)
        f1_benign = f1_score(y_test, y_pred, pos_label=1)

        write(f'', f)
        write(f'  +{"─"*20}+{"─"*12}+{"─"*12}+{"─"*12}+', f)
        write(f'  | {"Metric":<18} | {"Phishing":>10} | {"Benign":>10} | {"Overall":>10} |', f)
        write(f'  +{"─"*20}+{"─"*12}+{"─"*12}+{"─"*12}+', f)
        write(f'  | {"Precision":<18} | {prec_phish*100:>9.2f}% | {prec_benign*100:>9.2f}% | {prec_w*100:>9.2f}% |', f)
        write(f'  | {"Recall":<18} | {rec_phish*100:>9.2f}% | {rec_benign*100:>9.2f}% | {rec_w*100:>9.2f}% |', f)
        write(f'  | {"F1-Score":<18} | {f1_phish*100:>9.2f}% | {f1_benign*100:>9.2f}% | {f1_w*100:>9.2f}% |', f)
        write(f'  +{"─"*20}+{"─"*12}+{"─"*12}+{"─"*12}+', f)
        write(f'  | {"Accuracy":<18} |            |            | {acc*100:>9.2f}% |', f)
        write(f'  | {"AUC-ROC":<18} |            |            | {auc*100:>9.2f}% |', f)
        write(f'  +{"─"*20}+{"─"*12}+{"─"*12}+{"─"*12}+', f)

        # Confusion Matrix
        write(f'\n  Confusion Matrix:', f)
        cm = confusion_matrix(y_test, y_pred)
        write(f'                      Predicted', f)
        write(f'                  Phishing  Benign', f)
        write(f'  Actual Phishing  {cm[0][0]:>6,}  {cm[0][1]:>6,}', f)
        write(f'  Actual Benign    {cm[1][0]:>6,}  {cm[1][1]:>6,}', f)
        write(f'', f)
        write(f'  True Positives (TP):   {cm[0][0]:,}', f)
        write(f'  False Negatives (FN):  {cm[0][1]:,}  (Missed phishing)', f)
        write(f'  False Positives (FP):  {cm[1][0]:,}  (Safe flagged as phishing)', f)
        write(f'  True Negatives (TN):   {cm[1][1]:,}', f)

        # ────────────────────────────────────────────
        # 4. Processing Time Benchmark
        # ────────────────────────────────────────────
        section('4. Processing Time Benchmark', f)

        # Single prediction time
        single_times = []
        test_sample = X_test.iloc[:100]
        for i in range(100):
            row = test_sample.iloc[[i]]
            t0 = time.perf_counter()
            model.predict(row)
            model.predict_proba(row)
            t1 = time.perf_counter()
            single_times.append((t1 - t0) * 1000)

        avg_single = np.mean(single_times)
        p50_single = np.percentile(single_times, 50)
        p95_single = np.percentile(single_times, 95)
        p99_single = np.percentile(single_times, 99)

        write(f'  Single URL Prediction (100 samples):', f)
        write(f'    Average:    {avg_single:.3f} ms', f)
        write(f'    Median:     {p50_single:.3f} ms', f)
        write(f'    P95:        {p95_single:.3f} ms', f)
        write(f'    P99:        {p99_single:.3f} ms', f)

        # Batch prediction time
        batch_sizes = [100, 500, 1000, 5000]
        write(f'\n  Batch Prediction:', f)
        write(f'  +{"─"*12}+{"─"*15}+{"─"*18}+{"─"*15}+', f)
        write(f'  | {"Batch Size":>10} | {"Total Time":>13} | {"Per URL":>16} | {"URLs/sec":>13} |', f)
        write(f'  +{"─"*12}+{"─"*15}+{"─"*18}+{"─"*15}+', f)

        for bs in batch_sizes:
            batch = X_test.iloc[:bs]
            t0 = time.perf_counter()
            model.predict(batch)
            model.predict_proba(batch)
            t1 = time.perf_counter()
            total_ms = (t1 - t0) * 1000
            per_url = total_ms / bs
            urls_sec = bs / (t1 - t0)
            write(f'  | {bs:>10,} | {total_ms:>10.2f} ms | {per_url:>13.4f} ms | {urls_sec:>10,.0f}/s |', f)

        write(f'  +{"─"*12}+{"─"*15}+{"─"*18}+{"─"*15}+', f)

        # End-to-End Response Time (comparable to base paper)
        # Full pipeline: raw URL -> feature extraction -> prediction -> result
        from ml_predictor import MLPredictor
        predictor_bench = MLPredictor(MODEL_PATH)

        test_urls = df['URL'].dropna().iloc[:500].tolist()

        # Measure feature extraction time
        feat_times = []
        for url in test_urls[:100]:
            t0 = time.perf_counter()
            predictor_bench.extract_ml_features(url)
            t1 = time.perf_counter()
            feat_times.append((t1 - t0) * 1000)
        avg_feat = np.mean(feat_times)

        # Measure full response time (feature extraction + prediction)
        response_times = []
        for url in test_urls:
            t0 = time.perf_counter()
            predictor_bench.predict(url)
            t1 = time.perf_counter()
            response_times.append((t1 - t0) * 1000)

        avg_response = np.mean(response_times)
        p50_response = np.percentile(response_times, 50)
        p95_response = np.percentile(response_times, 95)
        p99_response = np.percentile(response_times, 99)
        min_response = np.min(response_times)
        max_response = np.max(response_times)

        write(f'', f)
        write(f'  End-to-End Response Time (500 real URLs from dataset):', f)
        write(f'  (raw URL -> feature extraction -> ML prediction -> result)', f)
        write(f'    Average Response Time:  {avg_response:.3f} ms', f)
        write(f'    Median Response Time:   {p50_response:.3f} ms', f)
        write(f'    P95 Response Time:      {p95_response:.3f} ms', f)
        write(f'    P99 Response Time:      {p99_response:.3f} ms', f)
        write(f'    Min Response Time:      {min_response:.3f} ms', f)
        write(f'    Max Response Time:      {max_response:.3f} ms', f)
        write(f'', f)
        write(f'  Time Breakdown:', f)
        write(f'    Feature Extraction:     {avg_feat:.3f} ms ({avg_feat/avg_response*100:.1f}%)', f)
        write(f'    ML Prediction:          {avg_response - avg_feat:.3f} ms ({(avg_response-avg_feat)/avg_response*100:.1f}%)', f)

        # ────────────────────────────────────────────
        # 5. Resource Usage
        # ────────────────────────────────────────────
        section('5. Resource Usage', f)

        # Memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        proc_mem = process.memory_info()

        write(f'  Memory Usage:', f)
        write(f'    Process RSS:        {proc_mem.rss / (1024*1024):.1f} MB', f)
        write(f'    Process VMS:        {proc_mem.vms / (1024*1024):.1f} MB', f)
        write(f'    Python Tracked:     {current_mem / (1024*1024):.1f} MB', f)
        write(f'    Python Peak:        {peak_mem / (1024*1024):.1f} MB', f)
        write(f'    Model File Size:    {model_size_mb:.2f} MB', f)

        # CPU during prediction — use a sampling thread to measure while work runs
        import threading

        cpu_samples = []
        stop_sampling = threading.Event()

        def sample_cpu():
            """Sample CPU usage every 100ms while predictions run."""
            process.cpu_percent(interval=None)  # initialize counter
            while not stop_sampling.is_set():
                time.sleep(0.1)
                cpu_samples.append(process.cpu_percent(interval=None))

        sampler = threading.Thread(target=sample_cpu, daemon=True)
        sampler.start()

        t0 = time.perf_counter()
        for _ in range(5):
            model.predict(X_test)
            model.predict_proba(X_test)
        t1 = time.perf_counter()

        stop_sampling.set()
        sampler.join(timeout=1)

        avg_cpu = np.mean(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0

        total_predictions = len(X_test) * 5
        total_cores = psutil.cpu_count(logical=True)

        write(f'\n  CPU Stress Test ({total_predictions:,} predictions, back-to-back):', f)
        write(f'    Avg CPU (this process): {avg_cpu:.1f}%', f)
        write(f'    Peak CPU (this process):{max_cpu:.1f}%', f)
        write(f'    System CPU Cores:       {total_cores}', f)
        write(f'    Actual System Load:     {avg_cpu/total_cores:.1f}% of total capacity', f)
        write(f'    Wall Time:              {(t1-t0)*1000:.0f} ms', f)
        write(f'    Throughput:             {total_predictions/(t1-t0):,.0f} URLs/sec', f)
        write(f'    NOTE: >100% means multiple cores used (Random Forest parallelism)', f)

        # Realistic usage: simulate a page scan (30 URLs, like a real web page)
        cpu_samples_real = []
        stop_real = threading.Event()

        def sample_cpu_real():
            process.cpu_percent(interval=None)
            while not stop_real.is_set():
                time.sleep(0.05)
                cpu_samples_real.append(process.cpu_percent(interval=None))

        sampler_real = threading.Thread(target=sample_cpu_real, daemon=True)
        sampler_real.start()

        t0_real = time.perf_counter()
        realistic_batch = X_test.iloc[:30]  # 30 URLs like a real page
        model.predict(realistic_batch)
        model.predict_proba(realistic_batch)
        t1_real = time.perf_counter()

        stop_real.set()
        sampler_real.join(timeout=1)

        avg_cpu_real = np.mean(cpu_samples_real) if cpu_samples_real else 0

        write(f'\n  Real-World Usage (single page scan, 30 URLs):', f)
        write(f'    CPU Usage:              {avg_cpu_real:.1f}%', f)
        write(f'    System Load:            {avg_cpu_real/total_cores:.1f}% of total capacity', f)
        write(f'    Processing Time:        {(t1_real-t0_real)*1000:.1f} ms', f)
        write(f'    NOTE: Typical page scan uses negligible CPU for <1 second', f)

        # ────────────────────────────────────────────
        # 6. Feature Importance
        # ────────────────────────────────────────────
        section('6. Feature Importance Ranking', f)

        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]

        write(f'  +{"─"*6}+{"─"*28}+{"─"*14}+{"─"*12}+', f)
        write(f'  | {"Rank":>4} | {"Feature":<26} | {"Importance":>12} | {"Cumul.":>10} |', f)
        write(f'  +{"─"*6}+{"─"*28}+{"─"*14}+{"─"*12}+', f)
        cumulative = 0
        for rank, idx in enumerate(indices, 1):
            cumulative += importances[idx]
            write(f'  | {rank:>4} | {FEATURE_COLUMNS[idx]:<26} | {importances[idx]:>11.4f} | {cumulative*100:>9.1f}% |', f)
        write(f'  +{"─"*6}+{"─"*28}+{"─"*14}+{"─"*12}+', f)

        # ────────────────────────────────────────────
        # 7. Real-World URL Evaluation
        # ────────────────────────────────────────────
        section('7. Real-World URL Evaluation', f)

        write(f'  Testing with FULL PIPELINE (Heuristic + ML + Blacklist + Whitelist)', f)
        write(f'  This reflects actual ScamShield behavior in production.', f)
        write(f'', f)

        from ml_predictor import MLPredictor
        from analyzer import classify_url
        from blacklist import BlacklistChecker

        predictor = MLPredictor(MODEL_PATH)

        # Set up blacklist for full pipeline
        import glob as _glob
        _bl_csv = None
        for _d in [os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), '..'), os.getcwd()]:
            _c = _glob.glob(os.path.join(_d, 'blacklist_dataset_cleaned*csv'))
            if _c:
                _bl_csv = _c[0]
                break
        bl_checker = BlacklistChecker(_bl_csv)

        correct_ml = 0      # ML-only accuracy
        correct_full = 0    # Full pipeline accuracy
        total_rw = len(REAL_WORLD_URLS)

        write(f'  +{"─"*55}+{"─"*10}+{"─"*10}+{"─"*12}+{"─"*8}+', f)
        write(f'  | {"URL":<53} | {"Expected":>8} | {"ML Only":>8} | {"Full Pipe":>10} | {"Match":>6} |', f)
        write(f'  +{"─"*55}+{"─"*10}+{"─"*10}+{"─"*12}+{"─"*8}+', f)

        for url, expected in REAL_WORLD_URLS:
            expected_label = 'safe' if expected == 'safe' else 'malicious'

            # ML-only prediction
            ml_result = predictor.predict(url)
            ml_got = ml_result['ml_prediction']
            if ml_got == expected_label:
                correct_ml += 1

            # Full pipeline: Heuristic → whitelist → ML blend → blacklist
            full_result = classify_url(url)
            # Apply blacklist
            bl_result = bl_checker.check_url(url)
            full_result['blacklisted'] = bl_result
            if bl_result['is_blacklisted']:
                full_result['classification'] = 'malicious'
                full_result['risk_score'] = 100
            else:
                # Apply trusted domain override (same logic as app.py)
                is_trusted = full_result.get('features', {}).get('is_trusted_domain', False)
                heuristic_score = full_result.get('risk_score', 0)
                if is_trusted and heuristic_score <= 5:
                    full_result['classification'] = 'safe'
                elif ml_result.get('ml_available'):
                    # Blend: 60% heuristic + 40% ML
                    ml_score = ml_result['ml_phishing_probability'] * 100
                    blended = (heuristic_score * 0.6) + (ml_score * 0.4)
                    if blended > 70:
                        full_result['classification'] = 'malicious'
                    elif blended > 35:
                        full_result['classification'] = 'suspicious'
                    else:
                        full_result['classification'] = 'safe'

            full_got = full_result['classification']
            # Map suspicious → malicious for comparison (both are "not safe")
            full_label = 'safe' if full_got == 'safe' else 'malicious'
            match_full = full_label == expected_label
            if match_full:
                correct_full += 1
            mark = '[OK]' if match_full else '[X]'
            write(f'  | {url[:53]:<53} | {expected:>8} | {ml_got:>8} | {full_got:>10} | {mark:>6} |', f)

        write(f'  +{"─"*55}+{"─"*10}+{"─"*10}+{"─"*12}+{"─"*8}+', f)
        write(f'  ML-Only Accuracy:    {correct_ml}/{total_rw} ({correct_ml/total_rw*100:.1f}%)', f)
        write(f'  Full Pipeline Accuracy: {correct_full}/{total_rw} ({correct_full/total_rw*100:.1f}%)', f)
        write(f'', f)
        write(f'  NOTE: The full pipeline uses trusted domain whitelisting and', f)
        write(f'  blended scoring (60% heuristic + 40% ML) to eliminate ML', f)
        write(f'  false positives on known-good domains like GitHub, StackOverflow.', f)

        correct = correct_full  # Use full pipeline for summary

        # ────────────────────────────────────────────
        # 8. Comparison Table Template
        # ────────────────────────────────────────────
        section('8. Comparison with Base Paper (Template)', f)

        write(f'  Fill in your base paper values in the "Base Paper" column.', f)
        write(f'  If you find other papers using the same dataset, add columns.', f)
        write(f'', f)
        write(f'  +{"─"*25}+{"─"*15}+{"─"*15}+{"─"*15}+', f)
        write(f'  | {"Metric":<23} | {"ScamShield":>13} | {"Base Paper":>13} | {"Paper 2":>13} |', f)
        write(f'  +{"─"*25}+{"─"*15}+{"─"*15}+{"─"*15}+', f)
        write(f'  | {"Accuracy":<23} | {acc*100:>12.2f}% | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Precision (Weighted)":<23} | {prec_w*100:>12.2f}% | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Recall (Weighted)":<23} | {rec_w*100:>12.2f}% | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"F1-Score (Weighted)":<23} | {f1_w*100:>12.2f}% | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"AUC-ROC":<23} | {auc*100:>12.2f}% | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Response Time (ms)":<23} | {avg_response:>10.3f} ms | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Model Size":<23} | {model_size_mb:>10.2f} MB | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Memory Usage":<23} | {proc_mem.rss/(1024*1024):>9.1f} MB | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Features Used":<23} | {len(FEATURE_COLUMNS):>13} | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Training Samples":<23} | {len(X_train):>13,} | {"---":>13} | {"---":>13} |', f)
        write(f'  | {"Algorithm":<23} | {"Random Forest":>13} | {"---":>13} | {"---":>13} |', f)
        write(f'  +{"─"*25}+{"─"*15}+{"─"*15}+{"─"*15}+', f)

        # ────────────────────────────────────────────
        # 9. Summary
        # ────────────────────────────────────────────
        section('9. Summary', f)

        write(f'  ScamShield achieves {acc*100:.2f}% accuracy on a dataset of', f)
        write(f'  {total:,} URLs ({n_phishing:,} phishing, {n_benign:,} benign).', f)
        write(f'', f)
        write(f'  Key Highlights:', f)
        write(f'    - F1-Score:               {f1_w*100:.2f}%', f)
        write(f'    - AUC-ROC:                {auc*100:.2f}%', f)
        write(f'    - Response Time:          {avg_response:.3f} ms per URL', f)
        write(f'    - Throughput:             {total_predictions/(t1-t0):,.0f} URLs/second', f)
        write(f'    - Memory footprint:       {proc_mem.rss/(1024*1024):.1f} MB', f)
        write(f'    - Real-world accuracy:    {correct/total_rw*100:.1f}%', f)
        write(f'', f)
        write(f'  Full report saved to: {OUTPUT_TXT}', f)

    # Save key metrics as CSV for easy import into reports
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Accuracy (%)', f'{acc*100:.2f}'])
        writer.writerow(['Precision - Weighted (%)', f'{prec_w*100:.2f}'])
        writer.writerow(['Recall - Weighted (%)', f'{rec_w*100:.2f}'])
        writer.writerow(['F1-Score - Weighted (%)', f'{f1_w*100:.2f}'])
        writer.writerow(['AUC-ROC (%)', f'{auc*100:.2f}'])
        writer.writerow(['Precision - Phishing (%)', f'{prec_phish*100:.2f}'])
        writer.writerow(['Recall - Phishing (%)', f'{rec_phish*100:.2f}'])
        writer.writerow(['F1-Score - Phishing (%)', f'{f1_phish*100:.2f}'])
        writer.writerow(['Response Time - Avg (ms)', f'{avg_response:.3f}'])
        writer.writerow(['Response Time - P95 (ms)', f'{p95_response:.3f}'])
        writer.writerow(['Feature Extraction Time (ms)', f'{avg_feat:.3f}'])
        writer.writerow(['ML Prediction Time (ms)', f'{avg_single:.3f}'])
        writer.writerow(['Throughput (URLs/sec)', f'{total_predictions/(t1-t0):,.0f}'])
        writer.writerow(['Memory RSS (MB)', f'{proc_mem.rss/(1024*1024):.1f}'])
        writer.writerow(['Model Size (MB)', f'{model_size_mb:.2f}'])
        writer.writerow(['Total Samples', f'{total}'])
        writer.writerow(['Features', f'{len(FEATURE_COLUMNS)}'])
        writer.writerow(['True Positives', f'{cm[0][0]}'])
        writer.writerow(['False Negatives', f'{cm[0][1]}'])
        writer.writerow(['False Positives', f'{cm[1][0]}'])
        writer.writerow(['True Negatives', f'{cm[1][1]}'])
        writer.writerow(['Real-World Accuracy (%)', f'{correct/total_rw*100:.1f}'])

    print(f'\n  CSV metrics saved to: {OUTPUT_CSV}')
    tracemalloc.stop()


if __name__ == '__main__':
    main()
