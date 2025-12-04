# RAG API Deployment - Complete Setup Summary

## ✅ What Has Been Configured

### 1. **FastAPI Application** (`src/API.py`)
- ✅ Graceful error handling for missing credentials
- ✅ CORS middleware configured
- ✅ Basic auth with environment variables
- ✅ Health check endpoint at `/health`
- ✅ Full API documentation at `/docs` and `/redoc`

### 2. **Service Files**
- ✅ `live_configuration/rag-api-dashboard.service` - Uvicorn service configured
- ✅ `live_configuration/rag-dashboard.service` - Flask service (unchanged)
- Both services share the same working directory: `/srv/rag-dashboard`

### 3. **Nginx Configuration**
- ✅ `/rag-api/` location block added to `live_configuration/fasolaki.com`
- ✅ Proxies to `127.0.0.1:8002` (Uvicorn server)
- ✅ Strips `/rag-api/` prefix before passing to app
- ✅ Proper headers forwarded (X-Forwarded-*, etc.)

### 4. **Python Dependencies**
- ✅ `uvicorn` in `requirements.txt` (already present)
- ✅ `fastapi` in `requirements.txt` (already present)
- ✅ All other dependencies available

---

## 🚀 Production Deployment

### Option A: Automated (Recommended)
On the production server, run:
```bash
cd /srv/rag-dashboard
sudo bash deploy.sh
```

### Option B: Manual Steps
```bash
# 1. Update code
cd /srv/rag-dashboard
sudo git pull origin main

# 2. Update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 3. Deploy service files
sudo cp live_configuration/rag-dashboard.service /etc/systemd/system/
sudo cp live_configuration/rag-api-dashboard.service /etc/systemd/system/

# 4. Deploy Nginx config
sudo cp live_configuration/fasolaki.com /etc/nginx/sites-enabled/

# 5. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart rag-dashboard rag-api-dashboard
sudo nginx -t && sudo systemctl reload nginx
```

---

## 📋 Pre-Deployment Checklist

- [ ] `.env` file exists at `/srv/rag-dashboard/.env`
- [ ] `GOOGLE_API_KEY` is set in `.env`
- [ ] `API_USERS` is set in `.env` (e.g., `API_USERS=testuser:testpass`)
- [ ] `SECRET_KEY` is set in `.env`
- [ ] `/var/log/rag-api-dashboard/` directory exists with correct permissions
- [ ] Python virtual environment at `/srv/rag-dashboard/.venv/` is activated

---

## ✔️ Post-Deployment Verification

### 1. Check Services
```bash
sudo systemctl status rag-dashboard
sudo systemctl status rag-api-dashboard
```

### 2. Check Port Listening
```bash
sudo netstat -tuln | grep 8002
```

### 3. Test Health Endpoint
```bash
# Without authentication
curl https://www.fasolaki.com/rag-api/health

# With authentication
curl -u testuser:testpass https://www.fasolaki.com/rag-api/health
```

### 4. View Logs
```bash
# Flask app logs
sudo journalctl -u rag-dashboard -n 50 -f

# API app logs
sudo journalctl -u rag-api-dashboard -n 50 -f

# Nginx errors
sudo tail -50 /var/log/nginx/error.log
```

---

## 🔗 Access Points

| Service | URL | Auth |
|---------|-----|------|
| **Flask Web App** | `https://www.fasolaki.com/rag/` | No |
| **FastAPI Health** | `https://www.fasolaki.com/rag-api/health` | Yes (Basic) |
| **FastAPI Docs** | `https://www.fasolaki.com/rag-api/docs` | Yes (Basic) |
| **FastAPI ReDoc** | `https://www.fasolaki.com/rag-api/redoc` | Yes (Basic) |

---

## 📁 File Locations

### Development (Local Repository)
```
/Users/chrys/Projects/Google File Search Dashboard/
├── src/
│   ├── app.py                 # Flask web app
│   ├── API.py                 # FastAPI app
│   ├── google_file_search.py  # Google Genai integration
│   └── prompt_storage.py      # Prompt management
├── wsgi.py                    # WSGI entry point
├── requirements.txt           # Python dependencies
├── live_configuration/
│   ├── fasolaki.com          # Nginx config
│   ├── rag-dashboard.service  # Flask systemd service
│   ├── rag-api-dashboard.service  # API systemd service
│   └── fetch_files.sh         # Sync script from production
├── deploy.sh                  # Automated deployment script
├── DEPLOYMENT_GUIDE.md        # Detailed deployment guide
└── README.md
```

### Production Server
```
/srv/rag-dashboard/
├── Same structure as development
├── .venv/                     # Python virtual environment
├── .env                       # Environment variables
└── uploads/                   # Uploaded files

/etc/systemd/system/
├── rag-dashboard.service      # Copied from repo
└── rag-api-dashboard.service  # Copied from repo

/etc/nginx/sites-enabled/
└── fasolaki.com              # Copied from repo

/var/log/
├── rag-dashboard/
│   ├── access.log
│   └── error.log
└── rag-api-dashboard/
    ├── stdout.log
    └── stderr.log
```

---

## 🔧 Configuration Files

### `.env` Template
```bash
# Google API
GOOGLE_API_KEY=your-google-api-key-here

# API Authentication (comma-separated user:password pairs)
API_USERS=testuser:testpass,admin:adminpass

# Flask Secret Key
SECRET_KEY=your-random-secret-key-here

# Environment
FLASK_ENV=production
```

---

## 📊 Service Architecture

```
Internet (HTTPS)
      ↓
  Nginx (Port 443)
    ↙        ↘
/rag/        /rag-api/
  ↓            ↓
Flask        FastAPI
Gunicorn     Uvicorn
(Socket)   (127.0.0.1:8002)
```

---

## 🐛 Troubleshooting

### API Service Won't Start
```bash
# Check detailed error logs
sudo tail -100 /var/log/rag-api-dashboard/stderr.log

# Try running manually
cd /srv/rag-dashboard
sudo -u deploy /srv/rag-dashboard/.venv/bin/uvicorn \
  --host 127.0.0.1 --port 8002 src.API:app
```

### Nginx Won't Reload
```bash
# Validate config
sudo nginx -t

# Check syntax errors
sudo nginx -T
```

### Port Already in Use
```bash
# Find process using port 8002
sudo lsof -i :8002

# Kill if needed
sudo kill -9 <PID>
```

### Authentication Issues
```bash
# Verify API_USERS format in .env
cat /srv/rag-dashboard/.env | grep API_USERS

# Test with curl
curl -u testuser:testpass http://127.0.0.1:8002/health
```

---

## 📚 Additional Resources

- **DEPLOYMENT_GUIDE.md** - Comprehensive deployment documentation
- **deploy.sh** - Automated deployment script for production
- **API Documentation** - Available at `/rag-api/docs` after deployment
- **Git History** - Check git log for recent deployment changes

---

## 🎯 Next Steps

1. **Test on Production**: Run the deployment and verify all services start
2. **Monitor Logs**: Watch logs for any errors during initial startup
3. **Load Test**: Test the API endpoints to ensure they work under load
4. **Backup Configuration**: Make regular backups of configuration files
5. **Set Up Monitoring**: Consider adding health check monitoring

---

**Last Updated**: December 4, 2025
**Status**: Ready for Production Deployment ✅
