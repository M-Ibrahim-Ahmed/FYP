# 🛡️ ScamShield — Real-Time Malicious URL Detection & Safe Browsing System

A Chrome Extension + Python Backend + Machine Learning system that detects phishing and malicious URLs in real-time.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chrome Extension                         │
│  content_script.js → background.js → popup.html/popup.js   │
│  (Crawler)           (Service Worker)  (Dashboard UI)       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST /analyze
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend (app.py)                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │  Blacklist    │ │  Heuristic   │ │  Random Forest ML    ││
│  │  Checker      │→│  Analyzer    │→│  Predictor           ││
│  │ (blacklist.py)│ │(analyzer.py) │ │(ml_predictor.py)     ││
│  └──────────────┘ └──────────────┘ └──────────────────────┘│
│  ┌──────────────┐ ┌──────────────────────┐                  │
│  │  MongoDB      │ │  Safe Preview        │                  │
│  │  (db.py)      │ │  (safe_preview.py)   │                  │
│  └──────────────┘ └──────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## ⚙️ 3-Stage Detection Pipeline

| Stage | Module | Description |
|-------|--------|-------------|
| 1️⃣ Blacklist | `blacklist.py` | Checks URLs against known phishing domains from `blacklist_dataset_cleaned (2).csv` |
| 2️⃣ Heuristics | `analyzer.py` | Scores URLs based on 14+ features (length, entropy, special chars, IP address, TLD, etc.) |
| 3️⃣ ML Model | `ml_predictor.py` | Random Forest classifier trained on 16 URL features. Blends with heuristic score (60% ML / 40% heuristic) |

**Classification thresholds:** Safe (≤20) → Suspicious (21-55) → Malicious (>55)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Google Chrome** (for the extension)
- **MongoDB** (optional — system works without it)
- **Docker** (optional — for safe preview and full deployment)

### 1. Install Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The server starts at `http://localhost:5000`. You'll see a status banner showing which components loaded.

### 2. Install Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **"Load unpacked"**
4. Select the `extension/` folder (this directory)
5. The ScamShield icon (🛡️) appears in your toolbar

### 3. Use It

- Navigate to any webpage
- Click the **ScamShield** icon to open the dashboard
- Click **"Scan Page"** to analyze all links, forms, images, redirects, and iframes
- Results show risk classification with color-coded cards:
  - 🟢 **Safe** — no issues detected
  - 🟡 **Suspicious** — proceed with caution
  - 🔴 **Malicious** — avoid this URL

---

## 🐳 Docker Deployment (Full Stack)

```bash
docker-compose up --build
```

This starts:
- **Flask backend** on port `5000`
- **MongoDB** on port `27017`
- **Selenium Chrome** on port `4444` (safe preview sandbox)

---

## 📁 Project Structure

```
extension/
├── manifest.json            # Chrome MV3 manifest
├── content_script.js        # Webpage crawler (extracts links, forms, images, etc.)
├── background.js            # Service worker (routes data to backend)
├── popup.html               # Dashboard UI
├── popup.js                 # Dashboard logic (analyzed + raw renderers)
├── styles.css               # Premium dark-mode CSS
├── icons/                   # Extension icons (16/48/128px)
│
├── backend/
│   ├── app.py               # Flask API (routes + pipeline orchestration)
│   ├── analyzer.py          # Heuristic URL analyzer (14+ rules)
│   ├── blacklist.py         # Blacklist checker (CSV + defaults)
│   ├── ml_predictor.py      # Random Forest ML predictions
│   ├── train_model.py       # Model training script
│   ├── db.py                # MongoDB integration
│   ├── safe_preview.py      # Selenium screenshot service
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container image
│
├── rf_phishing_model.pkl                  # Trained Random Forest model
├── blacklist_dataset_cleaned (2).csv      # Phishing URL blacklist
├── processed_scam_url_dataset (1).csv     # ML training dataset
├── url_features_extracted1.csv            # Extracted features dataset
├── docker-compose.yml                     # Full stack orchestration
└── README.md                              # This file
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health + component status |
| `POST` | `/analyze` | Analyze full page crawl data (JSON payload from extension) |
| `POST` | `/check` | Check a single URL through the 3-stage pipeline |
| `GET` | `/history?page=1&per_page=20` | Paginated scan history (requires MongoDB) |
| `GET` | `/stats` | Aggregate statistics (requires MongoDB) |
| `POST` | `/preview` | Capture safe screenshot of a URL (requires Selenium) |

## 🧠 Re-Training the ML Model

```bash
cd backend
python train_model.py
```

This reads from `url_features_extracted1.csv`, trains a Random Forest (100 trees, balanced classes), and saves to `rf_phishing_model.pkl`.

## 📊 Features Extracted by the Crawler

| Category | Elements |
|----------|----------|
| **Links** | All `<a>` tags with href, text, rel, target |
| **Forms** | Action URL, method, input fields, sensitive data flag |
| **Images** | Clickable images with destination URLs |
| **Redirects** | Meta refresh + JavaScript-based redirects |
| **iFrames** | Source URL, sandbox attribute, hidden status |

---

## 👤 Author

**Muhammad Ibrahim** — Final Year Project (FYP)

---
