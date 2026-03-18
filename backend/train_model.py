# train_model.py — ScamShield ML Training Script
# Trains a Random Forest classifier on the phishing URL dataset.
# Usage: python train_model.py

import os
import sys
import math
import re
from urllib.parse import urlparse, parse_qs
from collections import Counter

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib

# ─── Configuration ───
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'url_features_extracted1.csv')
MODEL_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rf_phishing_model.pkl')

# Feature columns (16 features matching the model)
FEATURE_COLUMNS = [
    'url_length', 'has_ip_address', 'dot_count', 'https_flag',
    'url_entropy', 'token_count', 'subdomain_count', 'query_param_count',
    'tld_length', 'path_length', 'has_hyphen_in_domain', 'number_of_digits',
    'tld_popularity', 'suspicious_file_extension', 'domain_name_length',
    'percentage_numeric_chars',
]
LABEL_COLUMN = 'ClassLabel'


def main():
    print('=' * 60)
    print('  ScamShield — Random Forest Model Training')
    print('=' * 60)

    # ─── Load dataset ───
    print(f'\n📂 Loading dataset from: {DATASET_PATH}')
    if not os.path.exists(DATASET_PATH):
        print(f'❌ Dataset not found at {DATASET_PATH}')
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    print(f'   Total samples: {len(df):,}')
    print(f'   Columns: {list(df.columns)}')

    # Drop rows with missing labels
    df = df.dropna(subset=[LABEL_COLUMN])
    print(f'   After dropping NaN labels: {len(df):,}')
    print(f'   Class distribution:')
    print(f'     Class 0 (Phishing): {(df[LABEL_COLUMN] == 0).sum():,}')
    print(f'     Class 1 (Benign):   {(df[LABEL_COLUMN] == 1).sum():,}')

    # ─── Prepare features and labels ───
    X = df[FEATURE_COLUMNS].copy()
    y = df[LABEL_COLUMN].astype(int)

    # Handle any NaN values in features
    X = X.fillna(0)

    print(f'\n📊 Feature matrix shape: {X.shape}')

    # ─── Train/test split ───
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f'   Training samples: {len(X_train):,}')
    print(f'   Test samples:     {len(X_test):,}')

    # ─── Train Random Forest ───
    print('\n🌲 Training Random Forest classifier...')
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,  # Use all CPU cores
        class_weight='balanced',  # Handle class imbalance
    )
    model.fit(X_train, y_train)
    print('   ✅ Training complete!')

    # ─── Evaluate ───
    print('\n📈 Evaluation Results:')
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f'   Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)')
    print()
    print('   Classification Report:')
    print(classification_report(y_test, y_pred, target_names=['Phishing (0)', 'Benign (1)'], indent=4))

    print('   Confusion Matrix:')
    cm = confusion_matrix(y_test, y_pred)
    print(f'     Phishing correctly detected: {cm[0][0]:,}')
    print(f'     Phishing missed (FN):        {cm[0][1]:,}')
    print(f'     Benign marked phishing (FP): {cm[1][0]:,}')
    print(f'     Benign correctly labeled:    {cm[1][1]:,}')

    # ─── Feature importance ───
    print('\n🔍 Feature Importance (top 10):')
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    for rank, idx in enumerate(indices[:10], 1):
        print(f'   {rank}. {FEATURE_COLUMNS[idx]}: {importances[idx]:.4f}')

    # ─── Save model ───
    print(f'\n💾 Saving model to: {MODEL_OUTPUT_PATH}')
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f'   Model size: {os.path.getsize(MODEL_OUTPUT_PATH) / (1024 * 1024):.2f} MB')
    print()
    print('✅ Done! Model saved successfully.')


if __name__ == '__main__':
    main()
