# ScamShield — Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  VPS / Cloud Server (Docker Host)                       │
│                                                         │
│  ┌─────────────────────┐   ┌─────────────────────────┐ │
│  │  Flask Backend       │──▶│  Selenium Chrome         │ │
│  │  (scamshield-backend)│   │  (sandbox browser)       │ │
│  │  Port 5000           │   │  Port 4444               │ │
│  │                      │   │                          │ │
│  │  • ML Model          │   │  Opens suspicious URLs   │ │
│  │  • Blacklist          │   │  safely in isolation     │ │
│  │  • Heuristic Analyzer │   │  Returns screenshots     │ │
│  └─────────────────────┘   └─────────────────────────┘ │
│                                                         │
│  docker-compose.yml                                     │
└─────────────────────────────────────────────────────────┘
          ▲
          │ HTTPS / HTTP
          │
┌─────────────────────────┐
│  User's Browser          │
│  Chrome Extension        │
│  (ScamShield)            │
└─────────────────────────┘
```

## Quick Start (Local)

```powershell
# 1. Make sure Docker Desktop is running

# 2. Build and start both containers
cd c:\ScamSheild\extension
docker compose up --build -d

# 3. Check status
docker compose ps

# 4. Test health
curl http://localhost:5000/health

# 5. Test Safe Preview
curl -X POST http://localhost:5000/preview -H "Content-Type: application/json" -d "{\"url\": \"https://www.google.com\"}"

# 6. Stop
docker compose down
```

## Deploy to a VPS

### Option 1: Oracle Cloud Free Tier (Recommended — Free Forever)

1. **Create an account** at [cloud.oracle.com](https://cloud.oracle.com)
2. **Launch a free VM**:
   - Shape: `VM.Standard.E2.1.Micro` (free)
   - OS: Ubuntu 22.04
   - RAM: 1 GB (enough for Flask + Selenium)

3. **SSH into the VM** and install Docker:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

4. **Clone your repo**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ScamShield.git
   cd ScamShield/extension
   ```

5. **Start the services**:
   ```bash
   docker compose up --build -d
   ```

6. **Open firewall port 5000**:
   - Oracle Cloud Console → Networking → VCN → Security Lists → Add Ingress Rule
   - Source: `0.0.0.0/0`, Protocol: TCP, Port: `5000`

7. **Update the Chrome extension** — change `BACKEND_URL` in these files:
   - `background.js` line 8
   - `popup.js` line 32
   - `content_script.js` line 478

   ```javascript
   const BACKEND_URL = 'http://YOUR_VPS_PUBLIC_IP:5000';
   ```

### Option 2: DigitalOcean ($4-6/month)

1. Create a Droplet (Ubuntu 22.04, 1GB RAM)
2. Follow steps 3-7 above

### Option 3: AWS EC2 Free Tier

1. Launch a `t2.micro` instance (free for 12 months)
2. Follow steps 3-7 above

## Verify Deployment

```bash
# From your local machine, test the deployed backend:
curl http://YOUR_VPS_IP:5000/health

# Test Safe Preview:
curl -X POST http://YOUR_VPS_IP:5000/preview \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.google.com"}'

# Check logs:
ssh your-vps
cd ScamShield/extension
docker compose logs -f
```

## Useful Commands

```bash
# View logs (live)
docker compose logs -f

# View logs for specific service
docker compose logs backend
docker compose logs selenium

# Restart services
docker compose restart

# Rebuild after code changes
docker compose up --build -d

# Stop everything
docker compose down

# Check resource usage
docker stats
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Backend can't connect to Selenium | Check `docker compose ps` — selenium should be "healthy" |
| Safe Preview times out | Increase `PREVIEW_TIMEOUT` env var (default: 25s) |
| Out of memory on VPS | Selenium needs ~500MB. Use a 2GB+ RAM instance |
| Extension can't reach backend | Check firewall/security group rules for port 5000 |
| Port 5000 already in use | Change port mapping in `docker-compose.yml` |
