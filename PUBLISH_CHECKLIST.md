# ScamShield - Publishing Checklist

## ✅ Status: Extension is READY!

All backend issues are fixed. Your Docker setup is production-ready.

---

## 📝 Publishing Checklist

### Phase 1: Deploy Backend (15 minutes)
- [ ] Push code to GitHub
- [ ] Deploy on Railway.app (or DigitalOcean)
- [ ] Get public URL (e.g., `https://your-app.railway.app`)
- [ ] Test backend health: `/health` endpoint

### Phase 2: Update Extension (5 minutes)
- [ ] Update `popup.js` line 32 with production URL
- [ ] Update `background.js` line 9 with production URL  
- [ ] Update `content_script.js` line 503 with production URL
- [ ] Test extension with production backend

### Phase 3: Create Assets (1 hour)
- [ ] Take 3-5 screenshots (extension popup, warnings, history)
- [ ] Create small tile image (440×280 px)
- [ ] Write privacy policy HTML
- [ ] Host privacy policy on GitHub Pages

### Phase 4: Package (5 minutes)
- [ ] Create ZIP with only extension files
- [ ] Include: manifest.json, *.js, *.html, *.css, icons/
- [ ] Exclude: backend/, datasets/, models/, docs/

### Phase 5: Submit (30 minutes)
- [ ] Pay $5 Chrome Developer fee
- [ ] Upload ZIP to Chrome Web Store
- [ ] Fill store listing (name, description, category)
- [ ] Upload screenshots and promotional images
- [ ] Add privacy policy URL
- [ ] Justify permissions
- [ ] Submit for review

### Phase 6: Wait & Launch (1-3 days)
- [ ] Wait for Chrome review
- [ ] Fix any issues if rejected
- [ ] Extension goes live!
- [ ] Share your Chrome Web Store link

---

## 🎯 Priority Order

### Do FIRST:
1. Deploy backend to Railway → **Start here!**
2. Update 3 files with production URL
3. Test extension thoroughly

### Do SECOND:
4. Create screenshots
5. Write privacy policy
6. Package ZIP

### Do LAST:
7. Submit to Chrome Store
8. Wait for approval

---

## 🔗 Important URLs

**Deployment:**
- Railway: https://railway.app
- DigitalOcean: https://digitalocean.com

**Chrome Store:**
- Developer Console: https://chrome.google.com/webstore/devconsole
- Documentation: https://developer.chrome.com/docs/webstore/

**Privacy Policy Hosting:**
- GitHub Pages: https://pages.github.com

---

## 💡 Files to Update

Replace `http://localhost:5000` with your production URL in:
1. `popup.js` (line 32)
2. `background.js` (line 9)
3. `content_script.js` (line 503)

---

## 📦 Files to Include in ZIP

✅ Include:
- manifest.json
- popup.html, popup.js
- background.js
- content_script.js
- styles.css
- icons/ folder

❌ Exclude:
- backend/ folder
- datasets/ folder
- models/ folder
- docs/ folder
- All .py files
- .git folder

---

## ⏱️ Total Time: ~2.5 hours work + 1-3 days review

**Cost: $5 one-time fee**

---

## 🚀 Quick Start Command

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Ready for deployment"
git remote add origin https://github.com/YOUR_USERNAME/scamshield.git
git push -u origin main

# 2. Deploy on Railway
# (Use Railway website - connect GitHub repo)

# 3. Update URLs in extension files
# (Edit manually or use find & replace)

# 4. Create ZIP
# (Select files, right-click → Compress)

# 5. Submit
# Visit: chrome.google.com/webstore/devconsole
```

---

**Need help? Check:**
- `DEPLOYMENT_SUMMARY.md` (complete guide)
- `CHROME_STORE_GUIDE.md` (detailed instructions)
- `FIXES_APPLIED.md` (what was fixed today)

---

**You're ready to publish! 🎉**
