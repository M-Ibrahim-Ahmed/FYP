# 🚀 ScamShield - Go Live Checklist

Follow this step-by-step checklist to publish your extension.

---

## ✅ PHASE 1: Deploy Backend (15-20 minutes)

### Task 1.1: Railway Setup
- [ ] Open https://railway.app
- [ ] Click "Login with GitHub"
- [ ] Authorize Railway to access your GitHub

### Task 1.2: Deploy Project
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub repo"
- [ ] Choose: `M-Ibrahim-Ahmed/FYP`
- [ ] Select branch: `dev`
- [ ] Click "Deploy"

### Task 1.3: Generate Domain
- [ ] Wait for deployment to start (1-2 minutes)
- [ ] Click "backend" service card
- [ ] Go to "Settings" tab
- [ ] Scroll to "Networking" section
- [ ] Click "Generate Domain"
- [ ] **📋 COPY YOUR URL**: `https://backend-production-XXXX.up.railway.app`

### Task 1.4: Wait for Build
- [ ] Go to "Deployments" tab
- [ ] Wait for build to complete (5-10 minutes)
- [ ] Status shows: ✅ **Active**

### Task 1.5: Test Backend
- [ ] Open: `https://YOUR-RAILWAY-URL.up.railway.app/health`
- [ ] Should see JSON with `"status": "ok"`
- [ ] Check: `"blacklist_size": 59933`
- [ ] Check: `"ml_model_loaded": true`

**✅ Backend is live!**

**Write your Railway URL here:**
```
_____________________________________________________
```

---

## ✅ PHASE 2: Update Extension (5 minutes)

You need to update 3 JavaScript files with your Railway URL.

### Task 2.1: Update popup.js
- [ ] Open `popup.js` in your editor
- [ ] Find line 32: `const BACKEND_URL = 'http://localhost:5000';`
- [ ] Replace with: `const BACKEND_URL = 'https://YOUR-RAILWAY-URL.up.railway.app';`
- [ ] Save file

### Task 2.2: Update background.js
- [ ] Open `background.js` in your editor
- [ ] Find line 9: `const BACKEND_URL = 'http://localhost:5000';`
- [ ] Replace with: `const BACKEND_URL = 'https://YOUR-RAILWAY-URL.up.railway.app';`
- [ ] Save file

### Task 2.3: Update content_script.js
- [ ] Open `content_script.js` in your editor
- [ ] Find line 503: `fetch('http://localhost:5000/preview', {`
- [ ] Replace with: `fetch('https://YOUR-RAILWAY-URL.up.railway.app/preview', {`
- [ ] Save file

**✅ Extension files updated!**

---

## ✅ PHASE 3: Test Extension with Production Backend (10 minutes)

### Task 3.1: Reload Extension
- [ ] Open Chrome
- [ ] Go to `chrome://extensions/`
- [ ] Find ScamShield extension
- [ ] Click reload icon (🔄)

### Task 3.2: Test on Website
- [ ] Visit: https://www.google.com
- [ ] Click ScamShield icon
- [ ] Wait for scan to complete
- [ ] Should show risk analysis (not "backend offline")

### Task 3.3: Test Features
- [ ] Check if links are classified (safe/suspicious/malicious)
- [ ] Click "History" tab - should show stats
- [ ] Try "Preview" on a link - should load screenshot
- [ ] Check browser console (F12) - no red errors

**✅ Extension works with production backend!**

---

## ✅ PHASE 4: Create Store Assets (60 minutes)

### Task 4.1: Take Screenshots (20 minutes)
- [ ] Screenshot 1: Extension popup showing risk analysis
- [ ] Screenshot 2: Link interception modal with warning
- [ ] Screenshot 3: History tab with statistics
- [ ] Screenshot 4: Visual threat indicators on page
- [ ] Screenshot 5: Safe preview feature (optional)

**Save as:** `screenshot1.png`, `screenshot2.png`, etc.
**Size:** 1280×800px or 640×400px

### Task 4.2: Create Promotional Tile (20 minutes)
- [ ] Go to https://canva.com (free account)
- [ ] Create design: Custom size 440×280px
- [ ] Add your icon (from `icons/icon128.png`)
- [ ] Add text: "ScamShield"
- [ ] Add tagline: "Real-Time Phishing Protection"
- [ ] Download as PNG: `promo-small.png`

Optional (recommended):
- [ ] Create large tile: 920×680px → `promo-large.png`

### Task 4.3: Write Privacy Policy (20 minutes)
- [ ] Create file: `privacy-policy.html`
- [ ] Copy template from `CHROME_STORE_GUIDE.md`
- [ ] Update with your email and GitHub link
- [ ] Host on GitHub Pages:
  1. Create new repo: `scamshield-privacy`
  2. Upload `privacy-policy.html`
  3. Enable Pages in Settings
  4. Get URL: `https://M-Ibrahim-Ahmed.github.io/scamshield-privacy/privacy-policy.html`

**Write your privacy policy URL here:**
```
_____________________________________________________
```

**✅ Store assets ready!**

---

## ✅ PHASE 5: Package Extension (5 minutes)

### Task 5.1: Create ZIP File
- [ ] Select ONLY these files/folders:
  - ✅ manifest.json
  - ✅ popup.html
  - ✅ popup.js (with updated URL)
  - ✅ background.js (with updated URL)
  - ✅ content_script.js (with updated URL)
  - ✅ styles.css
  - ✅ icons/ folder

- [ ] Right-click → "Send to" → "Compressed (zipped) folder"
- [ ] Name it: `scamshield.zip`

**DO NOT INCLUDE:**
- ❌ backend/ folder
- ❌ datasets/ folder
- ❌ models/ folder
- ❌ docs/ folder
- ❌ .git/ folder
- ❌ Any .py files

**✅ ZIP file created!**

---

## ✅ PHASE 6: Submit to Chrome Web Store (30 minutes)

### Task 6.1: Create Developer Account
- [ ] Go to: https://chrome.google.com/webstore/devconsole
- [ ] Sign in with your Google account
- [ ] Pay $5 registration fee (one-time)
- [ ] Complete developer profile

### Task 6.2: Upload Extension
- [ ] Click "New Item" button
- [ ] Upload `scamshield.zip`
- [ ] Wait for upload to complete (1-2 minutes)

### Task 6.3: Fill Product Details
- [ ] **Name:** ScamShield - Phishing Detector & Link Scanner
- [ ] **Summary:** 
  ```
  Real-time phishing detection using AI. Scans webpages for malicious links, forms, and threats.
  ```
- [ ] **Description:** (Copy from CHROME_STORE_GUIDE.md)
- [ ] **Category:** Security & Privacy → Security
- [ ] **Language:** English

### Task 6.4: Upload Graphics
- [ ] Upload screenshots (min 1, max 5)
- [ ] Upload small tile (440×280px) - REQUIRED
- [ ] Upload large tile (920×680px) - optional
- [ ] Extension icon auto-detected from manifest ✅

### Task 6.5: Privacy Settings
- [ ] **Privacy Policy URL:** (paste your GitHub Pages URL)
- [ ] **Permissions Justification:**
  ```
  • activeTab: Scan current page content for phishing threats
  • storage: Cache scan results for performance
  • scripting: Inject visual threat warnings on page
  • notifications: Alert users about dangerous sites
  • all_urls: Analyze external links on any website
  ```
- [ ] **Single Purpose Description:**
  ```
  Protect users from phishing attacks by scanning webpages in real-time.
  ```

### Task 6.6: Distribution
- [ ] **Visibility:** Public
- [ ] **Countries:** All regions
- [ ] **Pricing:** Free

### Task 6.7: Submit for Review
- [ ] Review all information
- [ ] Click "Submit for Review"
- [ ] Confirm submission

**✅ Extension submitted!**

---

## ⏰ PHASE 7: Wait for Approval (1-3 days)

### What Happens Next:
- [ ] Google reviews your extension (1-3 business days)
- [ ] You'll receive email updates on review status
- [ ] Possible outcomes:
  - ✅ **Approved** → Extension goes live immediately!
  - ⚠️ **Rejected** → Fix issues and resubmit

### If Rejected:
- [ ] Read rejection email carefully
- [ ] Fix the issues mentioned
- [ ] Update ZIP file
- [ ] Resubmit from dashboard

---

## 🎉 PHASE 8: Launch! (After Approval)

### Once Approved:
- [ ] Extension goes live on Chrome Web Store
- [ ] You get public URL: `https://chrome.google.com/webstore/detail/[your-extension-id]`
- [ ] Share the link with users
- [ ] Users can install with one click
- [ ] Auto-updates work automatically

### Post-Launch:
- [ ] Monitor Railway backend (keep it running!)
- [ ] Check Chrome Web Store reviews
- [ ] Respond to user feedback
- [ ] Update blacklist regularly
- [ ] Add to your resume/portfolio! 🎓

---

## 📊 Progress Tracker

**Overall Progress:**

- [ ] Phase 1: Deploy Backend (15-20 min)
- [ ] Phase 2: Update Extension (5 min)
- [ ] Phase 3: Test Extension (10 min)
- [ ] Phase 4: Create Assets (60 min)
- [ ] Phase 5: Package ZIP (5 min)
- [ ] Phase 6: Submit to Store (30 min)
- [ ] Phase 7: Wait for Approval (1-3 days)
- [ ] Phase 8: Launch! 🚀

**Total Active Time:** ~2-2.5 hours
**Total Timeline:** 1 week (including review wait)

---

## 💡 Quick Tips

✅ **Do:**
- Test thoroughly with production backend before submitting
- Take clear, high-quality screenshots
- Write accurate, honest description
- Respond quickly if rejected
- Keep backend server running 24/7

❌ **Don't:**
- Exaggerate claims in description
- Include trademark violations in images
- Skip testing with production URL
- Forget to update all 3 JavaScript files
- Let Railway backend go down

---

## 🆘 Get Help

**Railway Issues:**
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway

**Chrome Store Issues:**
- Help: https://developer.chrome.com/docs/webstore/
- Support: https://support.google.com/chrome_webstore/

**Backend Issues:**
- Check Railway logs
- Verify health endpoint
- Test API endpoints

---

## 🎯 Current Status

**What's Done:**
- ✅ Extension works locally
- ✅ Docker setup running
- ✅ Code pushed to GitHub
- ✅ All files ready

**What's Next:**
- ⏳ Deploy to Railway (START HERE!)
- ⏳ Update extension files
- ⏳ Create store assets
- ⏳ Submit to Chrome Store

---

**You're ready to go live! Start with Phase 1 (Railway deployment).** 🚀

**Estimated time to have extension live: 1 week** (2-3 hours work + 1-3 days review)
