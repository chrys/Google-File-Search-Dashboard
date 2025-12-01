"""
WSGI entry point for Gunicorn
This file is used to run the Flask application with Gunicorn in production
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env or .env.production
env_file = '.env.production' if os.getenv('FLASK_ENV') == 'production' else '.env'
env_path = os.path.join(os.path.dirname(__file__), env_file)

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the Flask app
from app import app

if __name__ == "__main__":
    # For development use only - use gunicorn in production
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        print("⚠️  Running in production mode without Gunicorn!")
        print("    Use: gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app")
    else:
        print("✓ Running in development mode")
        app.run(debug=app.config['DEBUG'], port=5000)
