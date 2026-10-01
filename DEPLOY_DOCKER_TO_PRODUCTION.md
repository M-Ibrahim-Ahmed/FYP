# Deploying ScamShield Docker Setup to Production

## ✅ Your Current Setup

You're running:
- **backend-1**: Flask API on port 5000
- **selenium-1**: Selenium Chrome on port 4444 (for safe previews)

This is **production-ready**! You just need to deploy these Docker containers to a public server.

---

## 🚀 Deployment Options (Easiest to Hardest)

### Option 1: Railway.app (Easiest, Recommended) ⭐

**Pros:**
- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Supports Docker Compose
- ✅ GitHub integration
- ✅ Takes 10 minutes

**Steps:**

1. **Push to GitHub** (if not already):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/scamshield.git
   git push -u origin main
   ```

2. **Go to Railway**:
   - Visit: https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your ScamShield repo

3. **Configure Services**:
   Railway will detect your `docker-compose.yml` and create both services!
   
   - Backend will get: `https://scamshield-backend.up.railway.app`
   - Both services will be on Railway's private network

4. **Environment Variables** (set in Railway dashboard):
   ```
   SELENIUM_REMOTE_URL=http://selenium:4444/wd/hub
   ```

5. **Get Your Public URL**:
   - Railway provides: `https://[random-name].up.railway.app`
   - This is your new `BACKEND_URL`!

**Cost:** Free for ~500 hours/month (good for FYP demo), then $5/month

---

### Option 2: Render.com (Also Easy)

**Pros:**
- ✅ Free tier
- ✅ Docker support
- ✅ Auto HTTPS
- ✅ Simple UI

**Steps:**

1. Push to GitHub (same as above)

2. Go to https://render.com
   - Sign up
   - New → Web Service
   - Connect GitHub repo

3. Configure:
   - **Environment:** Docker
   - **Dockerfile path:** `backend/Dockerfile`
   - **Port:** 5000

4. Add Selenium as separate service:
   - New → Web Service
   - **Image:** `selenium/standalone-chrome:latest`
   - **Port:** 4444

5. Connect them via Private Network

**Cost:** Free tier available

---

### Option 3: DigitalOcean Droplet (Most Control)

**Pros:**
- ✅ Full control
- ✅ Fixed IP address
- ✅ Good performance
- ✅ Can use Docker Compose directly

**Steps:**

1. **Create Droplet**:
   - Go to https://digitalocean.com
   - Create account
   - New Droplet → Docker image ($6/month)
   - Choose region closest to you

2. **SSH into Server**:
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

3. **Install Docker Compose** (if not included):
   ```bash
   apt update
   apt install docker-compose -y
   ```

4. **Clone Your Repo**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/scamshield.git
   cd scamshield
   ```

5. **Update Dockerfile** (fix file paths):
   ```bash
   nano backend/Dockerfile
   ```
   
   Change:
   ```dockerfile
   # OLD:
   COPY rf_phishing_model.pkl .
   COPY url_features_extracted1.csv .
   COPY ["blacklist_dataset_cleaned (2).csv", "."]
   
   # NEW (correct paths based on your file structure):
   COPY models/rf_phishing_model.pkl .
   COPY datasets/url_features_extracted1.csv .
   COPY datasets/blacklist_dataset_cleaned.csv blacklist_dataset_cleaned.csv
   ```

6. **Start Services**:
   ```bash
   docker-compose up -d --build
   ```

7. **Check Status**:
   ```bash
   docker ps
   curl http://localhost:5000/health
   ```

8. **Configure Firewall**:
   ```bash
   ufw allow 5000/tcp
   ufw allow 4444/tcp
   ufw enable
   ```

9. **Your Backend URL**:
   ```
   http://YOUR_DROPLET_IP:5000
   ```

**Optional: Add Domain + HTTPS**:
   - Point domain to droplet IP
   - Install Nginx + Let's Encrypt
   - Proxy port 5000 → https://yourdomain.com

**Cost:** $6/month (basic droplet)

---

### Option 4: AWS EC2 (Professional)

Similar to DigitalOcean but:
- More complex setup
- Free tier for 1 year
- Better for scaling later

**Quick Steps:**
1. Launch EC2 instance (Ubuntu, t2.micro for free tier)
2. Install Docker + Docker Compose
3. Clone repo and run `docker-compose up -d`
4. Configure Security Group (allow ports 5000, 4444)
5. Use Elastic IP for fixed address

---

## 🔧 Required Dockerfile Fixes

Your current `backend/Dockerfile` has incorrect file paths. Update it:

<function_calls>
<invoke name="strReplace">
<parameter name="path">backend/Dockerfile