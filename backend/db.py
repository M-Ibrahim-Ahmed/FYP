# db.py — ScamShield MongoDB Integration
# Provides connection helpers and CRUD operations for scan results.

import os
import time
from datetime import datetime, timezone

try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False

# ─── Configuration ───
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://scamshield:ch.1ScamShield@scamshield.d60uuiz.mongodb.net/?appName=ScamShield'
)
MONGO_DB = os.environ.get('MONGO_DB', 'scamshield')
MONGO_TIMEOUT_MS = 5000  # 5s for cloud latency


class Database:
    """MongoDB wrapper for ScamShield scan storage."""

    def __init__(self):
        self.client = None
        self.db = None
        self.available = False

        if not HAS_MONGO:
            print('[ScamShield DB] pymongo not installed — database features disabled')
            return

        try:
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
                connectTimeoutMS=MONGO_TIMEOUT_MS,
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[MONGO_DB]
            self.available = True
            self._ensure_indexes()
            print(f'[ScamShield DB] Connected to MongoDB ({MONGO_URI}/{MONGO_DB})')
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f'[ScamShield DB] MongoDB not available: {e}')
            print('[ScamShield DB] Running without database — results will not be persisted')
        except Exception as e:
            print(f'[ScamShield DB] Unexpected error: {e}')

    def _ensure_indexes(self):
        """Create indexes for efficient queries."""
        if not self.available:
            return
        try:
            self.db.scans.create_index([('timestamp', DESCENDING)])
            self.db.scans.create_index([('page_url', 1)])
            self.db.urls.create_index([('url', 1)])
            self.db.urls.create_index([('classification', 1)])
            self.db.urls.create_index([('scanned_at', DESCENDING)])
        except Exception as e:
            print(f'[ScamShield DB] Index creation error: {e}')

    # ─── Save Operations ───

    def save_scan(self, analysis_result):
        """Save a complete page scan result to the 'scans' collection.

        Also saves individual URL classifications to the 'urls' collection.
        Returns the inserted scan _id or None.
        """
        if not self.available:
            return None

        try:
            scan_doc = {
                'page_url': analysis_result.get('page_url', ''),
                'page_title': analysis_result.get('page_title', ''),
                'timestamp': analysis_result.get('timestamp', ''),
                'scanned_at': datetime.now(timezone.utc),
                'summary': analysis_result.get('summary', {}),
                'link_count': len(analysis_result.get('links', [])),
                'form_count': len(analysis_result.get('forms', [])),
                'image_count': len(analysis_result.get('images', [])),
                'redirect_count': len(analysis_result.get('redirects', [])),
                'iframe_count': len(analysis_result.get('iframes', [])),
            }
            result = self.db.scans.insert_one(scan_doc)
            scan_id = result.inserted_id

            # Save individual URL classifications
            url_docs = []
            for category in ['links', 'forms', 'images', 'redirects', 'iframes']:
                for item in analysis_result.get(category, []):
                    url_docs.append({
                        'scan_id': scan_id,
                        'url': item.get('url', ''),
                        'classification': item.get('classification', 'unknown'),
                        'risk_score': item.get('risk_score', 0),
                        'source_category': category,
                        'blacklisted': item.get('blacklisted', {}).get('is_blacklisted', False),
                        'ml_prediction': item.get('ml', {}).get('ml_prediction'),
                        'ml_confidence': item.get('ml', {}).get('ml_confidence', 0),
                        'scanned_at': datetime.now(timezone.utc),
                    })

            if url_docs:
                self.db.urls.insert_many(url_docs, ordered=False)

            return str(scan_id)
        except Exception as e:
            print(f'[ScamShield DB] Save error: {e}')
            return None

    # ─── Query Operations ───

    def get_history(self, page=1, per_page=20):
        """Get paginated scan history (most recent first)."""
        if not self.available:
            return {'scans': [], 'total': 0, 'page': page, 'per_page': per_page}

        try:
            skip = (page - 1) * per_page
            total = self.db.scans.count_documents({})
            cursor = self.db.scans.find(
                {},
                {'_id': 0}  # exclude MongoDB _id from output
            ).sort('scanned_at', DESCENDING).skip(skip).limit(per_page)

            scans = []
            for doc in cursor:
                # Convert datetime to ISO string for JSON serialization
                if 'scanned_at' in doc and hasattr(doc['scanned_at'], 'isoformat'):
                    doc['scanned_at'] = doc['scanned_at'].isoformat()
                scans.append(doc)

            return {
                'scans': scans,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, (total + per_page - 1) // per_page),
            }
        except Exception as e:
            print(f'[ScamShield DB] History query error: {e}')
            return {'scans': [], 'total': 0, 'page': page, 'per_page': per_page}

    def get_stats(self):
        """Get aggregate statistics across all scans."""
        if not self.available:
            return {'available': False}

        try:
            total_scans = self.db.scans.count_documents({})
            total_urls = self.db.urls.count_documents({})

            # Classification breakdown
            safe_count = self.db.urls.count_documents({'classification': 'safe'})
            suspicious_count = self.db.urls.count_documents({'classification': 'suspicious'})
            malicious_count = self.db.urls.count_documents({'classification': 'malicious'})
            blacklisted_count = self.db.urls.count_documents({'blacklisted': True})

            # Recent scans (last 5)
            recent = list(self.db.scans.find(
                {}, {'_id': 0, 'page_url': 1, 'summary': 1, 'scanned_at': 1}
            ).sort('scanned_at', DESCENDING).limit(5))

            for doc in recent:
                if 'scanned_at' in doc and hasattr(doc['scanned_at'], 'isoformat'):
                    doc['scanned_at'] = doc['scanned_at'].isoformat()

            return {
                'available': True,
                'total_scans': total_scans,
                'total_urls_analyzed': total_urls,
                'classifications': {
                    'safe': safe_count,
                    'suspicious': suspicious_count,
                    'malicious': malicious_count,
                },
                'blacklisted_urls': blacklisted_count,
                'recent_scans': recent,
            }
        except Exception as e:
            print(f'[ScamShield DB] Stats query error: {e}')
            return {'available': False, 'error': str(e)}

    @property
    def is_available(self):
        return self.available
