# Deploy ScamShield to Railway.app - Step by Step

## ✅ Prerequisites (Done!)
- ✅ Code pushed to GitHub: https://github.com/M-Ibrahim-Ahmed/FYP
- ✅ Docker setup working locally
- ✅ All files ready

---

## 🚂 Step-by-Step Railway Deployment

### STEP 1: Create Railway Account (2 minutes)

1. **Go to Railway.app**
   - Open: https://railway.app
   - Click **"Start a New Project"** or **"Login"**

2. **Sign Up with GitHub**
   - Click **"Login with GitHub"**
   - Authorize Railway to access your GitHub account
   - This connects your repos automatically

3. **Verify Email** (if prompted)

✅ **You're now logged into Railway!**

---

### STEP 2: Create New Project (3 minutes)

1. **Click "New Project"** button (big + icon on dashboard)

2. **Select "Deploy from GitHub repo"**

3. **Choose your repository:**
   - Find: `M-Ibrahim-Ahmed/FYP`
   - Click on it
   - Select branch: **`dev`** (your current branch)

4. **Railway will scan your repo** and detect:
   - ✅ `docker-compose.yml` found!
   - ✅ Will create 2 services: backend + selenium

5. **Click "Deploy"**

⏳ **Railway is now setting up your project...**

---

### STEP 3: Configure Services (5 minutes)

After deployment starts, Railway creates 2 services. Let's configure them:

#### A. Configure Backend Service

1. **Click on the "backend" service** card

2. **Go to "Settings" tab**

3. **Generate Public Domain:**
   - Scroll to "Networking" section
   - Click **"Generate Domain"**
   - Railway creates: `backend-production-XXXX.up.railway.app`
   - **📋 COPY THIS URL** - you'll need it!

4. **Set Environment Variables** (if needed):
   - Click "Variables" tab
   - Should auto-detect `SELENIUM_REMOTE_URL=http://selenium:4444/wd/hub`
   - This is correct ✅

5. **Check "Deployments" tab**
   - Wait for build to complete (5-10 minutes first time)
   - Status should show: ✅ **Active**

#### B. Selenium Service (Auto-configured)

The Selenium service is automatically configured by Railway:
- ✅ Runs on private network (backend can access it)
- ✅ No public domain needed (internal only)
- ✅ Connected via `http://selenium:4444`

---

### STEP 4: Verify Deployment (2 minutes)

1. **Check Backend Health:**
   - Copy your Railway URL: `https://backend-production-XXXX.up.railway.app`
   - Add `/health` to the end
   - Open in browser: `https://backend-production-XXXX.up.railway.app/health`

2. **You should see:**
   ```json
   {
     "status": "ok",
     "service": "ScamShield Backend",
     "version": "1.0",
     "blacklist_size": 59933,
     "ml_model_loaded": true
   }
   ```

✅ **Backend is live!**

---

### STEP 5: Test All Endpoints (Optional)

Test these URLs in your browser (replace with YOUR Railway URL):

```
https://your-backend.up.railway.app/health
https://your-backend.up.railway.app/stats
https://your-backend.up.railway.app/history
```

All should return JSON responses.

---

## 🎯 Your Production URL

**Write down your Railway URL here:**
```
https://backend-production-XXXX.up.railway.app
```

**This is your new BACKEND_URL for the Chrome extension!**

---

## 💰 Railway Pricing

Railway offers:
- **Free tier:** $5 credit per month (good for testing/FYP demo)
- **Usage-based:** ~$5-10/month for light usage
- **First month:** Usually free due to credits

**For your FYP demo**, the free tier should be sufficient!

---

## 🔍 Monitoring Your App

**Railway Dashboard shows:**
- ✅ Deployment status
- ✅ Build logs
- ✅ Runtime logs (click "View Logs")
- ✅ Resource usage (CPU, memory)
- ✅ Metrics

**To view logs:**
1. Click on "backend" service
2. Click "Deployments" tab
3. Click "View Logs"
4. See real-time output

---

## 🐛 Troubleshooting

### Build Failed?

**Check logs:**
1. Click service → Deployments → View Logs
2. Look for red error messages

**Common issues:**
- **File not found:** Check Dockerfile paths
- **Out of memory:** Upgrade Railway plan
- **Port issues:** Railway auto-assigns ports (should work)

### Backend Shows "Crashed"?

**Check:**
1. View logs for Python errors
2. Verify all dependencies in `requirements.txt`
3. Check if files copied correctly (models/, datasets/)

### Can't Access URL?

**Verify:**
1. Domain is generated (Settings → Networking)
2. Service is "Active" (not "Crashed")
3. Health check passes: `/health`

---

## ✅ Success Checklist

- [ ] Railway account created
- [ ] Project deployed from GitHub
- [ ] Backend service has public domain
- [ ] Health endpoint returns 200 OK
- [ ] Blacklist loaded (59,933 entries)
- [ ] ML model loaded successfully
- [ ] Selenium connected (check logs)
- [ ] Production URL copied for extension update

---

## 🚀 Next Step

Once your backend is live and health check passes, proceed to:

**→ Update Extension Files** (next step in main guide)

Your Railway URL will replace `http://localhost:5000` in 3 files.

---

## 📞 Need Help?

**Railway Support:**
- Help docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Twitter: @Railway

**Common Railway Commands:**
```bash
# Install Railway CLI (optional)
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs

# Check status
railway status
```

---

**Railway deployment is the easiest option!** Most FYP projects use it successfully.

Good luck! 🎓
