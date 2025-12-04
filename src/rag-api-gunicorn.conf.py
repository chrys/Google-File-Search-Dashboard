import os

# Gunicorn configuration for FastAPI app (running uvicorn workers)
bind = "127.0.0.1:8001"  # Local binding for development
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Environment
env = {
    "PYTHONUNBUFFERED": "1",
}