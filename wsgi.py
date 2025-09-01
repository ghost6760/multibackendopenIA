"""WSGI entry point for Railway production server - Enhanced Error Handling"""

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

def check_environment():
    """Check Railway environment and log important info"""
    logger.info("🚄 Railway WSGI Startup")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📂 Working directory: {os.getcwd()}")
    logger.info(f"🔧 Environment: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'unknown')}")
    logger.info(f"🌐 Port: {os.getenv('PORT', '8080')}")
    
    # List available files for debugging
    if os.path.exists('.'):
        files = os.listdir('.')
        logger.info(f"📁 Available files: {files}")
    
    if os.path.exists('app'):
        app_files = os.listdir('app')
        logger.info(f"📁 App directory: {app_files}")

def check_dependencies():
    """Check if critical dependencies are available"""
    required_packages = [
        'flask',
        'flask_cors',
        'openai',
        'redis',
        'langchain',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} imported successfully")
        except ImportError as e:
            logger.error(f"❌ Missing package: {package} - {e}")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"💥 CRITICAL: Missing packages: {missing_packages}")
        logger.error("🔧 Check requirements.txt and rebuild")
        raise ImportError(f"Missing critical packages: {missing_packages}")
    
    logger.info("✅ All required packages available")

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Log environment info
    check_environment()
    
    # Check dependencies first
    check_dependencies()
    
    logger.info("🚀 Starting WSGI application...")
    
    # Import the app factory with enhanced error handling
    try:
        from app import create_app
        logger.info("✅ App factory imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import app factory: {e}")
        logger.error(f"📂 Current sys.path: {sys.path}")
        raise
    
    # Import configuration
    try:
        from app.config.settings import config
        logger.info("✅ Configuration imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import configuration: {e}")
        # Try alternative import
        try:
            from app.config import Config
            config = {'default': Config, 'production': Config, 'development': Config}
            logger.info("✅ Alternative configuration loaded")
        except ImportError:
            logger.error("❌ No configuration available - using basic Flask")
            config = {'default': None}
    
    # Get environment
    env = os.getenv('FLASK_ENV', 'production')
    railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', 'production')
    logger.info(f"🔧 Flask environment: {env}")
    logger.info(f"🚄 Railway environment: {railway_env}")
    
    # Create the Flask app with error handling
    try:
        if config.get(env):
            app = create_app(config[env])
        else:
            app = create_app()
        logger.info("✅ Flask app created successfully")
        
        # Test the app
        with app.app_context():
            logger.info("✅ App context test successful")
            
    except Exception as e:
        logger.error(f"❌ Failed to create Flask app: {e}")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        
        # Try to create a minimal Flask app for debugging
        logger.info("🔧 Attempting to create minimal Flask app...")
        try:
            from flask import Flask, jsonify
            app = Flask(__name__)
            
            @app.route('/health')
            def health():
                return jsonify({
                    "status": "minimal",
                    "message": "Basic Flask app running",
                    "error": "Main application failed to initialize"
                })
            
            @app.route('/')
            def root():
                return jsonify({
                    "status": "error",
                    "message": "Application initialization failed",
                    "suggestion": "Check logs and requirements"
                })
                
            logger.info("✅ Minimal Flask app created as fallback")
            
        except Exception as fallback_error:
            logger.error(f"💥 Even minimal Flask app failed: {fallback_error}")
            raise
    
    logger.info("🎉 WSGI application ready for Railway")
    
except Exception as e:
    logger.error(f"💥 CRITICAL WSGI ERROR: {e}")
    logger.error(f"📋 Full traceback: {traceback.format_exc()}")
    
    # Log system information for debugging
    logger.error(f"🖥️ System info:")
    logger.error(f"   - Python executable: {sys.executable}")
    logger.error(f"   - Python path: {sys.path}")
    logger.error(f"   - Working directory: {os.getcwd()}")
    logger.error(f"   - Environment variables: {dict(os.environ)}")
    
    # Don't re-raise in production to avoid complete failure
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        logger.error("🚄 Creating emergency Flask app for Railway")
        
        try:
            from flask import Flask, jsonify
            app = Flask(__name__)
            
            @app.route('/health')
            def emergency_health():
                return jsonify({
                    "status": "emergency",
                    "message": "Emergency mode - main app failed",
                    "error": str(e)
                }), 503
            
            @app.route('/')
            def emergency_root():
                return jsonify({
                    "status": "emergency", 
                    "message": "Application in emergency mode",
                    "error": "Check Railway logs for details"
                }), 503
                
        except:
            raise e
    else:
        raise

# Railway compatibility check
if hasattr(app, 'wsgi_app'):
    logger.info("✅ WSGI app attribute available")
else:
    logger.info("ℹ️ Using Flask app directly")

# This is what Gunicorn will import
application = app

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Starting development server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
