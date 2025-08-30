"""WSGI entry point for production server - Fixed for Railway"""

import os
import sys
import logging

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Add the app directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    logger.info("🚀 Starting WSGI application...")
    
    # Import the app factory
    from app import create_app
    from app.config.settings import config
    
    # Get environment
    env = os.getenv('FLASK_ENV', 'production')
    logger.info(f"Environment: {env}")
    
    # Create the Flask app
    app = create_app(config.get(env, config['default']))
    
    logger.info("✅ WSGI application created successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to create WSGI application: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Python path: {sys.path}")
    logger.error(f"Available files: {os.listdir('.')}")
    if os.path.exists('app'):
        logger.error(f"App directory contents: {os.listdir('app')}")
    raise

# This is what Gunicorn will import
if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
