# ScamShield - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Python Dependencies

```bash
cd backend
pip install flask flask-cors python-dotenv joblib scikit-learn numpy selenium
```

### Step 2: Start the Backend Server

```bash
python app.py
```

You should see:
```
=======================================================
  [*] ScamShield Backend Server
=======================================================
  ML Model:     [OK] Loaded
  Blacklist:    59933 entries
  Preview:      [OK] API fallback
  Server:       http://localhost:5000
=======================================================
```

**✅ Backend is running at http://localhost:5000**

### Step 3: Load Extension in Chrome

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Toggle "Developer mode" ON (top-right corner)
4. Click "Load unpacked" button
5. Select your project folder (the one containing `manifest.json`)
6. Done! The ScamShield icon should appear in your toolbar

## 🧪 Test the Extension

### Basic Test
1. Visit any website (e.g., https://google.com)
2. Click the ScamShield extension icon
3. You should see:
   - Page analysis with risk score
   - List of links, forms, images, redirects, iframes
   - Risk badges (safe/suspicious/malicious)

### Test Malicious Link Detection
1. Visit a page with external links
2. Click the ScamShield icon
3. Look for links marked as "suspicious" or "malicious"
4. Click a suspicious link → you'll see an interception modal with safe preview option

### Test History & Stats
1. Scan a few different pages
2. Click the ScamShield icon
3. Go to the "History" tab
4. You should see statistics and recent scans

## 🔧 Troubleshooting

### "Backend offline" message in extension
**Problem:** Extension can't connect to backend server

**Solutions:**
1. Make sure backend is running: `cd backend && python app.py`
2. Check backend is at http://localhost:5000
3. Check for firewall blocking port 5000
4. Look for errors in backend terminal

### "ML Model not loaded"
**Problem:** Model file not found

**Solutions:**
1. Verify file exists: `ls models/rf_phishing_model.pkl`
2. Check backend startup logs for path being searched
3. Model should be in `models/` folder relative to project root

### "Blacklist not loaded" or size shows 0
**Problem:** Blacklist CSV not found

**Solutions:**
1. Verify file exists: `ls datasets/blacklist_dataset_cleaned.csv`
2. Check backend startup logs
3. File should be in `datasets/` folder

### Extension doesn't scan page automatically
**Possible causes:**
1. Page blocked content scripts (chrome://, about:, file://)
2. Backend not running
3. Check browser console (F12 → Console tab) for errors

### Preview feature not working
**Expected behavior:**
- Preview uses remote API (thum.io) by default
- First preview may take 10-15 seconds (waiting for page to load)
- Some sites block screenshot services

**To improve preview quality:**
1. Install Docker Desktop
2. Run: `docker-compose up -d` (starts Selenium container)
3. Backend will auto-detect and use Docker for better previews

## 📁 Project Structure

```
scamshield/
├── backend/              # Flask backend server
│   ├── app.py           # Main API routes ✅ FIXED
│   ├── analyzer.py      # Heuristic analysis
│   ├── blacklist.py     # Blacklist checker
│   ├── ml_predictor.py  # ML model inference
│   ├── safe_preview.py  # Safe URL preview
│   └── tests/           # Backend tests
├── datasets/            # Datasets for blacklist ✅ FIXED PATH
│   └── blacklist_dataset_cleaned.csv
├── models/              # ML models ✅ FIXED PATH
│   └── rf_phishing_model.pkl
├── icons/               # Extension icons
├── manifest.json        # Chrome extension manifest
├── popup.html          # Extension popup UI
├── popup.js            # Extension popup logic
├── content_script.js   # Page crawler
├── background.js       # Service worker
└── styles.css          # Extension styles
```

## 🎯 What's Working Now

✅ Backend server with all routes  
✅ 3-stage analysis pipeline (Blacklist → Heuristics → ML)  
✅ Browser extension auto-scan  
✅ Risk classification with badges  
✅ Link click interception for dangerous sites  
✅ Safe preview of suspicious URLs  
✅ Scan history tracking  
✅ Statistics dashboard  
✅ CSV export  
✅ In-page visual indicators  

## 📊 Testing with Known Phishing Sites

**⚠️ DANGER: DO NOT CLICK THESE LINKS DIRECTLY**

You can test the extension with known phishing test domains (safe to check, don't submit credentials):

1. PhishTank recent phishes: https://phishtank.org/
2. Use the "Check URL" feature in the extension
3. Paste a suspicious URL and see the classification

**Safe test:** Try these benign URLs that trigger heuristics:
- `http://192.168.1.1/login.php` (IP address + login keyword)
- `https://secure-paypal-verify-account-update.com` (suspicious keywords)

## 🚢 Deploying to Production (Optional)

### For Backend:
1. Get a VPS (AWS, DigitalOcean, Linode)
2. Install Docker on VPS
3. Copy project to VPS
4. Update `docker-compose.yml` with your domain
5. Run: `docker-compose up -d`

### For Extension:
1. Update `BACKEND_URL` in these files:
   - `popup.js` (line 20)
   - `background.js` (line 5)
   - `content_script.js` (line 120)
   
   Change from:
   ```javascript
   const BACKEND_URL = 'http://localhost:5000';
   ```
   
   To:
   ```javascript
   const BACKEND_URL = 'https://your-domain.com';
   ```

2. Publish to Chrome Web Store:
   - Create developer account ($5 one-time fee)
   - Zip the extension files
   - Upload to Chrome Web Store Developer Dashboard
   - Wait for review (~1-3 days)

## 💡 Tips

- **Development:** Keep backend terminal open to see logs in real-time
- **Debugging Extension:** Use Chrome DevTools (F12) on the extension popup
- **Testing:** Try different websites (news, social media, e-commerce)
- **Performance:** First scan may be slow while ML model loads, subsequent scans are fast

## 🆘 Still Having Issues?

Check these files for detailed information:
- `FIXES_APPLIED.md` - What was fixed and why
- `docs/README.md` - Full project documentation  
- `docs/DEPLOY.md` - Deployment guide

Or check backend logs:
```bash
cd backend
python app.py
# Watch for errors in red
```

---

**🎉 You're all set! Start scanning websites for threats.**
