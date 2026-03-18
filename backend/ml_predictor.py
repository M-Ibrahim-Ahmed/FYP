# ml_predictor.py — ScamShield ML Prediction Module
# Loads the trained Random Forest model and provides URL predictions.

import os
import math
import re
import warnings
from urllib.parse import urlparse, parse_qs
from collections import Counter

import numpy as np

# Suppress sklearn version warnings
warnings.filterwarnings('ignore', category=UserWarning)

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

# ─── TLD popularity mapping (higher = more popular/trusted) ───
TLD_POPULARITY = {
    'com': 10, 'org': 9, 'net': 8, 'edu': 9, 'gov': 10,
    'co': 7, 'io': 6, 'me': 5, 'info': 5, 'biz': 4,
    'us': 6, 'uk': 7, 'ca': 7, 'au': 7, 'de': 7, 'fr': 7,
    'in': 6, 'jp': 7, 'cn': 6, 'ru': 5, 'br': 6,
    'xyz': 2, 'top': 2, 'tk': 1, 'ml': 1, 'ga': 1, 'cf': 1,
    'gq': 1, 'pw': 1, 'cc': 2, 'club': 2, 'work': 2,
    'buzz': 1, 'surf': 1, 'icu': 1, 'cam': 1, 'bid': 1,
}

# Suspicious file extensions
SUSPICIOUS_EXTENSIONS = ['.exe', '.zip', '.scr', '.bat', '.cmd', '.js', '.vbs', '.php', '.cgi']


class MLPredictor:
    """Loads the trained Random Forest model and predicts phishing probability for URLs."""

    def __init__(self, model_path=None):
        self.model = None
        self.available = False

        if not HAS_JOBLIB:
            print('[ScamShield ML] joblib not installed — ML predictions disabled')
            return

        # Default model path
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'rf_phishing_model.pkl'
            )
            # Also check in the backend directory
            if not os.path.exists(model_path):
                model_path = os.path.join(os.path.dirname(__file__), '..', 'rf_phishing_model.pkl')

        model_path = os.path.abspath(model_path)

        if not os.path.exists(model_path):
            print(f'[ScamShield ML] Model file not found at {model_path}')
            return

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                self.model = joblib.load(model_path)
            self.available = True
            print(f'[ScamShield ML] Model loaded successfully ({self.model.n_features_in_} features)')
        except Exception as e:
            print(f'[ScamShield ML] Failed to load model: {e}')

    def extract_ml_features(self, url):
        """Extract the 16 features expected by the trained Random Forest model.

        Feature order (must match training):
        0. url_length
        1. has_ip_address
        2. dot_count
        3. https_flag
        4. url_entropy
        5. token_count
        6. subdomain_count
        7. query_param_count
        8. tld_length
        9. path_length
        10. has_hyphen_in_domain
        11. number_of_digits
        12. tld_popularity
        13. suspicious_file_extension
        14. domain_name_length
        15. percentage_numeric_chars
        """
        try:
            parsed = urlparse(url)
        except Exception:
            return [0] * 16

        domain = parsed.hostname or ''
        path = parsed.path or ''
        query = parsed.query or ''

        # 0. url_length
        url_length = len(url)

        # 1. has_ip_address (binary: 1 if IP, 0 if not)
        has_ip = 1 if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain) else 0

        # 2. dot_count
        dot_count = url.count('.')

        # 3. https_flag (1 if HTTPS, 0 if not)
        https_flag = 1 if parsed.scheme == 'https' else 0

        # 4. url_entropy (Shannon entropy of the full URL)
        url_entropy = self._shannon_entropy(url)

        # 5. token_count (number of tokens split by . / - _ ? = &)
        tokens = re.split(r'[.\-_/?=&]', url)
        token_count = len([t for t in tokens if t])

        # 6. subdomain_count
        subdomain_count = max(0, domain.count('.') - 1)

        # 7. query_param_count
        query_param_count = len(parse_qs(query))

        # 8. tld_length
        tld = domain.split('.')[-1] if '.' in domain else ''
        tld_length = len(tld)

        # 9. path_length
        path_length = len(path)

        # 10. has_hyphen_in_domain (binary)
        has_hyphen = 1 if '-' in domain else 0

        # 11. number_of_digits (in the full URL)
        number_of_digits = sum(c.isdigit() for c in url)

        # 12. tld_popularity (from lookup table)
        tld_popularity = TLD_POPULARITY.get(tld.lower(), 3)

        # 13. suspicious_file_extension (binary)
        suspicious_ext = 1 if any(path.lower().endswith(ext) for ext in SUSPICIOUS_EXTENSIONS) else 0

        # 14. domain_name_length
        domain_name_length = len(domain)

        # 15. percentage_numeric_chars
        percentage_numeric = (number_of_digits / max(len(url), 1)) * 100

        return [
            url_length,           # 0
            has_ip,               # 1
            dot_count,            # 2
            https_flag,           # 3
            url_entropy,          # 4
            token_count,          # 5
            subdomain_count,      # 6
            query_param_count,    # 7
            tld_length,           # 8
            path_length,          # 9
            has_hyphen,           # 10
            number_of_digits,     # 11
            tld_popularity,       # 12
            suspicious_ext,       # 13
            domain_name_length,   # 14
            percentage_numeric,   # 15
        ]

    def predict(self, url):
        """Predict whether a URL is phishing or benign.

        Returns:
            dict with 'ml_prediction' (safe/malicious), 'ml_confidence' (0-1),
            'ml_phishing_probability' (0-1), and 'ml_features'
        """
        if not self.available:
            return {
                'ml_available': False,
                'ml_prediction': None,
                'ml_confidence': 0,
                'ml_phishing_probability': 0,
            }

        features = self.extract_ml_features(url)
        feature_array = np.array(features).reshape(1, -1)

        try:
            prediction = self.model.predict(feature_array)[0]
            probabilities = self.model.predict_proba(feature_array)[0]

            # Class 0 = phishing, Class 1 = safe
            phishing_prob = float(probabilities[0])
            safe_prob = float(probabilities[1])

            ml_prediction = 'safe' if prediction == 1 else 'malicious'
            confidence = max(phishing_prob, safe_prob)

            return {
                'ml_available': True,
                'ml_prediction': ml_prediction,
                'ml_confidence': round(confidence, 4),
                'ml_phishing_probability': round(phishing_prob, 4),
                'ml_features': {
                    'url_length': features[0],
                    'has_ip_address': features[1],
                    'dot_count': features[2],
                    'https_flag': features[3],
                    'url_entropy': round(features[4], 4),
                    'token_count': features[5],
                    'subdomain_count': features[6],
                    'query_param_count': features[7],
                    'tld_length': features[8],
                    'path_length': features[9],
                    'has_hyphen_in_domain': features[10],
                    'number_of_digits': features[11],
                    'tld_popularity': features[12],
                    'suspicious_file_extension': features[13],
                    'domain_name_length': features[14],
                    'percentage_numeric_chars': round(features[15], 4),
                },
            }
        except Exception as e:
            return {
                'ml_available': False,
                'ml_prediction': None,
                'ml_confidence': 0,
                'ml_phishing_probability': 0,
                'ml_error': str(e),
            }

    @staticmethod
    def _shannon_entropy(text):
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0
        freq = Counter(text)
        length = len(text)
        return -sum((c / length) * math.log2(c / length) for c in freq.values())
