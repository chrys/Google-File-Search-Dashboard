# RAG API Deployment Guide

This guide explains how to deploy both the Flask Web App (RAG Dashboard) and the FastAPI (RAG API) to production.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         HTTPS (https://www.fasolaki.com)        │
│                   Nginx                          │
└──────────┬──────────────────────────┬────────────┘
           │                          │
      /rag/ prefix              /rag-api/ prefix
           │                          │
    ┌──────▼──────┐          ┌────────▼──────────┐
    │  Flask App  │          │   FastAPI App     │
    │  Gunicorn   │          │   Uvicorn         │
    │  Port 5000  │          │   Port 8002       │
    │ (Socket)    │          │ (localhost)       │
    └─────────────┘          └───────────────────┘
```

## Files Location

- **Development (Local)**: `/Users/chrys/Projects/Google File Search Dashboard/`
  - `src/app.py` - Flask Web Application
  - `src/API.py` - FastAPI Application
  - `wsgi.py` - WSGI entry point for Flask
  - `live_configuration/rag-dashboard.service` - Flask systemd service
  - `live_configuration/rag-api-dashboard.service` - FastAPI systemd service
  - `live_configuration/fasolaki.com` - Nginx configuration

- **Production**: `/srv/rag-dashboard/`
  - Same structure as local repo
  - Services copied to `/etc/systemd/system/`
  - Nginx config at `/etc/nginx/sites-enabled/fasolaki.com`

## Production Deployment Steps

### 1. Initial Setup (One-time)

```bash
# On production server, as root:

# Create directories
mkdir -p /var/log/rag-dashboard
mkdir -p /var/log/rag-api-dashboard

# Set permissions
chown deploy:www-data /var/log/rag-dashboard
chown deploy:www-data /var/log/rag-api-dashboard
chmod 755 /var/log/rag-dashboard
chmod 755 /var/log/rag-api-dashboard
```

### 2. Deploy Code Changes

```bash
# On production server, in /srv/rag-dashboard:
cd /srv/rag-dashboard
sudo git pull origin main

# Install or update Python dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Deploy Service Files

```bash
# On production server:

# Copy service files
sudo cp live_configuration/rag-dashboard.service /etc/systemd/system/
sudo cp live_configuration/rag-api-dashboard.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable rag-dashboard
sudo systemctl enable rag-api-dashboard
```

### 4. Deploy Nginx Configuration

```bash
# On production server:

# Copy Nginx config
sudo cp live_configuration/fasolaki.com /etc/nginx/sites-enabled/

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 5. Start Services

```bash
# On production server:

# Start both services
sudo systemctl restart rag-dashboard
sudo systemctl restart rag-api-dashboard

# Check status
sudo systemctl status rag-dashboard
sudo systemctl status rag-api-dashboard

# View logs
sudo journalctl -u rag-dashboard -f
sudo journalctl -u rag-api-dashboard -f
```

## Testing

### Test Flask Web App
```bash
curl https://www.fasolaki.com/rag/
```

### Test FastAPI with Basic Auth
```bash
curl -u testuser:testpass https://www.fasolaki.com/rag-api/health
```

### View API Documentation
```
https://www.fasolaki.com/rag-api/docs
https://www.fasolaki.com/rag-api/redoc
```

## Service Details

### Flask App (rag-dashboard.service)
- **Application**: `src/app.py`
- **WSGI Entry**: `wsgi.py`
- **Server**: Gunicorn (4 workers, sync)
- **Binding**: Unix socket at `/run/rag-dashboard/rag-dashboard.sock`
- **Ports**: Port 5000 (for local testing)
- **URL**: `https://www.fasolaki.com/rag/`

### FastAPI App (rag-api-dashboard.service)
- **Application**: `src/API.py`
- **Server**: Uvicorn (native ASGI)
- **Binding**: `127.0.0.1:8002`
- **URL**: `https://www.fasolaki.com/rag-api/`

## Environment Variables Required

Both services use the same `.env` file at `/srv/rag-dashboard/.env`:

```bash
# Google API
GOOGLE_API_KEY=<your-key>

# API Authentication
API_USERS=testuser:testpass,user2:pass2

# Flask
SECRET_KEY=<your-secret-key>
FLASK_ENV=production
```

## Troubleshooting

### API Service Won't Start
```bash
# Check detailed logs
sudo tail -100 /var/log/rag-api-dashboard/stderr.log
sudo tail -100 /var/log/rag-api-dashboard/stdout.log

# Run manually to see errors
cd /srv/rag-dashboard
sudo -u deploy .venv/bin/uvicorn --host 127.0.0.1 --port 8002 src.API:app
```

### API Not Responding
```bash
# Check if service is running
sudo systemctl status rag-api-dashboard

# Check if port is listening
sudo netstat -tuln | grep 8002

# Test local connection
sudo -u deploy curl http://127.0.0.1:8002/health
```

### Nginx Not Proxying
```bash
# Test Nginx config
sudo nginx -t

# Check Nginx is running
sudo systemctl status nginx

# View Nginx error log
sudo tail -50 /var/log/nginx/error.log
```

## Automatic Deployments

To automate future deployments:

```bash
# Create a deploy script on your local machine
# This pulls the latest code and restarts services

#!/bin/bash
ssh chrys@myVPS3 << 'EOF'
cd /srv/rag-dashboard
sudo git pull origin main
sudo systemctl daemon-reload
sudo systemctl restart rag-dashboard rag-api-dashboard
sudo nginx -t && sudo systemctl reload nginx
EOF
```

## Logs Locations

- **Flask App**: `/var/log/rag-dashboard/`
- **FastAPI App**: `/var/log/rag-api-dashboard/`
- **Nginx**: `/var/log/nginx/`
- **Systemd**: `sudo journalctl -u rag-dashboard` and `sudo journalctl -u rag-api-dashboard`
