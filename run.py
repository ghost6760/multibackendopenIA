#!/usr/bin/env python3
"""Development server runner - Fixed for Railway compatibility"""

import os
import sys
import logging

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from app import create_app
    from app.config.settings import config
    
    if __name__ == "__main__":
        # Get environment
        env = os.getenv('FLASK_ENV', 'development')
        logger.info(f"Starting development server in {env} mode")
        
        # Create the Flask app
        app_config = config.get(env, config['default'])
        app = create_app(app_config)
        
        # Get port from environment or use default
        port = int(os.getenv('PORT', 8080))
        
        # Run the development server
        app.run(
            host='0.0.0.0',
            port=port,
            debug=(env == 'development')
        )
        
except Exception as e:
    logger.error(f"Failed to start application: {e}")
    logger.error(f"Make sure app/config/settings.py exists")
    raise
