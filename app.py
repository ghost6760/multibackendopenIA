# app.py - Punto de entrada principal para Railway
import os
import sys
from app import create_app

# Configurar path para importar desde app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.logger.info(f"🚀 Starting Multi-Tenant Chatbot on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
