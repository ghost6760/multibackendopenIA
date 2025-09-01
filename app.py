# app.py - Servir React build en producción
from flask import Flask, send_from_directory, send_file
import os

app = Flask(__name__, static_folder='../frontend/build')

# Servir archivos estáticos de React
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """Servir la aplicación React en producción"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# APIs mantienen su prefijo /api/
@app.route('/api/health')
def health():
    return {"status": "healthy"}
