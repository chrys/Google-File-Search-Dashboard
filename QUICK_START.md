# 🚀 Quick Start: Deploy RAG API to Production

## One-Command Deployment
```bash
# SSH into production server and run:
ssh chrys@myVPS3
cd /srv/rag-dashboard && sudo bash deploy.sh
```

---

## ✅ What Gets Deployed

| Component | What | Where | How |
|-----------|------|-------|-----|
| **Flask Web** | `src/app.py` | `/rag/` | Gunicorn on socket |
| **FastAPI** | `src/API.py` | `/rag-api/` | Uvicorn on :8002 |
| **Nginx** | Config file | `/etc/nginx/sites-enabled/` | Proxies both apps |
| **Services** | Systemd files | `/etc/systemd/system/` | Auto-restart on reboot |

---

## 🔗 URLs After Deployment

```
https://www.fasolaki.com/rag/              → Flask Web App
https://www.fasolaki.com/rag-api/health    → API Health Check
https://www.fasolaki.com/rag-api/docs      → API Documentation (Swagger UI)
https://www.fasolaki.com/rag-api/redoc     → API Documentation (ReDoc)
```

---

## 🧪 Quick Tests

```bash
# Test Flask App
curl https://www.fasolaki.com/rag/ 2>/dev/null | grep -i "<!doctype\|<html"

# Test API without auth
curl https://www.fasolaki.com/rag-api/health 2>/dev/null

# Test API with auth
curl -u testuser:testpass https://www.fasolaki.com/rag-api/health 2>/dev/null
```

---

## 📋 Prerequisites

Before deploying, ensure:

```bash
# On production server, verify:
✓ Code is cloned to /srv/rag-dashboard
✓ Python venv exists at /srv/rag-dashboard/.venv
✓ .env file exists with API_USERS and GOOGLE_API_KEY
✓ /var/log/rag-api-dashboard/ directory exists
✓ deploy user has sudo access
✓ Nginx is installed and running
```

---

## 🔧 Manual Deployment (If Needed)

```bash
# Step 1: Pull code
cd /srv/rag-dashboard && sudo git pull origin main

# Step 2: Install dependencies
source .venv/bin/activate && pip install -r requirements.txt

# Step 3: Deploy files
sudo cp live_configuration/rag-api-dashboard.service /etc/systemd/system/
sudo cp live_configuration/fasolaki.com /etc/nginx/sites-enabled/

# Step 4: Restart services
sudo systemctl daemon-reload
sudo systemctl restart rag-api-dashboard
sudo nginx -t && sudo systemctl reload nginx

# Step 5: Verify
sudo systemctl status rag-api-dashboard
```

---

## 📊 Service Status

```bash
# Check if running
sudo systemctl is-active rag-api-dashboard

# View logs
sudo journalctl -u rag-api-dashboard -n 50 -f

# Check listening port
sudo netstat -tuln | grep 8002
```

---

## ⚙️ Environment Variables Required

Edit `/srv/rag-dashboard/.env`:

```bash
GOOGLE_API_KEY=your-api-key
API_USERS=testuser:testpass
SECRET_KEY=your-secret-key
FLASK_ENV=production
```

---

## 🐛 If Something Goes Wrong

```bash
# Most common issue: API_USERS not set
grep API_USERS /srv/rag-dashboard/.env

# Check if service crashed
sudo systemctl status rag-api-dashboard
sudo tail -50 /var/log/rag-api-dashboard/stderr.log

# Verify Nginx routing
sudo nginx -t

# Check firewall/port
sudo netstat -tuln | grep 8002
```

---

## 📂 Files Modified

```
✅ src/API.py - Graceful error handling
✅ src/google_file_search.py - Better error messages
✅ live_configuration/rag-api-dashboard.service - Uvicorn config
✅ live_configuration/fasolaki.com - Nginx /rag-api/ route
✅ deploy.sh - Automated deployment script (NEW)
✅ DEPLOYMENT_GUIDE.md - Full documentation (NEW)
✅ API_SETUP_SUMMARY.md - Setup reference (NEW)
```

---

## 📞 Support

For detailed information, see:
- `DEPLOYMENT_GUIDE.md` - Full deployment guide
- `API_SETUP_SUMMARY.md` - Complete setup reference
- `src/API.py` - API implementation

All changes are committed and pushed to production remote.
