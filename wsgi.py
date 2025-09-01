"""WSGI entry point for Railway production server - FINAL FIXED VERSION"""

import os
import sys
import logging
import traceback

# Configure enhanced logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    logger.info("🚀 Starting WSGI application...")
    
    # Import the FIXED app factory
    from app import create_app_with_railway_support
    
    # Get environment
    env = os.getenv('FLASK_ENV', 'production')
    railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', 'production')
    logger.info(f"🔧 Flask environment: {env}")
    logger.info(f"🚄 Railway environment: {railway_env}")
    
    # Create the Flask app with full Railway support and error handling
    app = create_app_with_railway_support()
    logger.info("✅ Flask app created successfully with Railway support")
    
    # Test the app
    with app.app_context():
        logger.info("✅ App context test successful")
    
    logger.info("🎉 WSGI application ready for Railway")
    
except Exception as e:
    logger.error(f"💥 CRITICAL WSGI ERROR: {e}")
    logger.error(f"📋 Full traceback: {traceback.format_exc()}")
    
    # Create emergency Flask app for Railway
    logger.error("🚄 Creating emergency Flask app for Railway")
    
    try:
        from flask import Flask, jsonify
        app = Flask(__name__)
        
        @app.route('/health')
        def emergency_health():
            return jsonify({
                "status": "emergency",
                "message": "Emergency mode - main app failed to initialize",
                "error": str(e),
                "environment": "railway"
            }), 503
        
        @app.route('/')
        def emergency_root():
            return jsonify({
                "status": "emergency", 
                "message": "Application in emergency mode",
                "error": "Main application failed to initialize",
                "suggestion": "Check Railway logs for details",
                "environment": "railway"
            }), 503
            
        logger.info("✅ Emergency Flask app created")
        
    except Exception as emergency_error:
        logger.error(f"💥 Even emergency Flask app failed: {emergency_error}")
        raise

# This is what Gunicorn will import
application = app

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Starting development server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
