#!/bin/bash
# deploy.sh - Script de despliegue completo para Railway
# Asegura que todos los archivos estén en su lugar antes del despliegue

set -e  # Exit on any error

echo "🚀 Preparando despliegue para Railway..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para logging
log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar estructura del proyecto
log_info "Verificando estructura del proyecto..."

# Verificar que existan los directorios principales
if [ ! -d "app" ]; then
    log_error "Falta el directorio 'app' (backend)"
    exit 1
fi

if [ ! -d "src" ]; then
    log_error "Falta el directorio 'src' (frontend)"
    exit 1
fi

log_info "Directorios principales encontrados"

# Verificar archivos críticos del backend
log_info "Verificando archivos del backend..."

required_backend_files=("wsgi.py" "run.py" "requirements.txt" "companies_config.json")
for file in "${required_backend_files[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Falta archivo crítico del backend: $file"
        exit 1
    fi
done

log_info "Archivos del backend verificados"

# Crear estructura del frontend si no existe
log_info "Preparando estructura del frontend..."

# Crear directorio public si no existe
mkdir -p src/public

# Verificar que exista package.json
if [ ! -f "src/package.json" ]; then
    log_error "Falta src/package.json"
    exit 1
fi

# Crear index.html si no existe
if [ ! -f "src/public/index.html" ]; then
    log_warn "Creando src/public/index.html faltante..."
    cat > src/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <meta name="description" content="Multi-Tenant Admin Interface" />
  <link rel="apple-touch-icon" href="%PUBLIC_URL%/logo192.png" />
  <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
  <title>Multi-Tenant Admin</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
EOF
    log_info "index.html creado"
fi

# Crear manifest.json si no existe
if [ ! -f "src/public/manifest.json" ]; then
    log_warn "Creando manifest.json faltante..."
    cat > src/public/manifest.json << 'EOF'
{
  "short_name": "MT Admin",
  "name": "Multi-Tenant Admin",
  "icons": [
    {
      "src": "favicon.ico",
      "sizes": "64x64 32x32 24x24 16x16",
      "type": "image/x-icon"
    }
  ],
  "start_url": "./",
  "display": "standalone",
  "theme_color": "#000000",
  "background_color": "#ffffff"
}
EOF
    log_info "manifest.json creado"
fi

# Crear robots.txt si no existe
if [ ! -f "src/public/robots.txt" ]; then
    cat > src/public/robots.txt << 'EOF'
User-agent: *
Disallow: /api/
Allow: /
EOF
    log_info "robots.txt creado"
fi

# Crear favicon vacío si no existe (para evitar errores)
if [ ! -f "src/public/favicon.ico" ]; then
    log_warn "Creando favicon.ico placeholder..."
    # Crear un favicon simple de 1x1 pixel transparente
    echo -e '\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' > src/public/favicon.ico
fi

# Verificar estructura final
log_info "Verificando estructura final..."

required_frontend_files=("src/package.json" "src/public/index.html" "src/index.js")
for file in "${required_frontend_files[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Falta archivo crítico del frontend: $file"
        exit 1
    fi
done

# Mostrar estructura final
log_info "Estructura del proyecto:"
echo "📁 Proyecto Multi-Tenant"
echo "├── 🐍 Backend (app/)"
echo "│   ├── ✅ wsgi.py"
echo "│   ├── ✅ run.py"
echo "│   ├── ✅ requirements.txt"
echo "│   └── ✅ companies_config.json"
echo "├── ⚛️ Frontend (src/)"
echo "│   ├── ✅ package.json"
echo "│   ├── ✅ index.js"
echo "│   └── 📁 public/"
echo "│       ├── ✅ index.html"
echo "│       ├── ✅ manifest.json"
echo "│       ├── ✅ robots.txt"
echo "│       └── ✅ favicon.ico"
echo "└── 🐳 Dockerfile"

log_info "¡Proyecto listo para despliegue en Railway!"

echo ""
echo "📋 Próximos pasos:"
echo "1. Commit y push de los cambios:"
echo "   git add ."
echo "   git commit -m 'feat: añadir estructura completa frontend para Railway'"
echo "   git push origin main"
echo ""
echo "2. Railway detectará automáticamente el Dockerfile y:"
echo "   ✅ Construirá el frontend React"
echo "   ✅ Instalará dependencias del backend"
echo "   ✅ Desplegará todo en un solo contenedor"
echo ""
echo "3. El build será exitoso y la app estará disponible en:"
echo "   https://tu-app-railway.up.railway.app"

# Test local opcional
read -p "¿Quieres hacer un test local del build? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Ejecutando test local..."
    cd src
    npm install
    npm run build
    log_info "Test local completado. Verifica que se creó src/build/"
    ls -la build/
fi
