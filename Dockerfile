# Dockerfile optimizado para Railway
FROM python:3.11-slim

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PORT=8080

# Instalar dependencias del sistema y limpiar en un solo paso para reducir tamaño de imagen
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential libssl-dev

# Copiar código de la aplicación
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Exponer puerto (Railway lo asigna dinámicamente)
EXPOSE $PORT

# Comando optimizado para Railway con variables de entorno
CMD gunicorn --bind 0.0.0.0:$PORT \
    --workers $(( $(nproc) * 2 + 1 )) \
    --threads 4 \
    --timeout 120 \
    --keep-alive 5 \
    --worker-class gthread \
    --access-logfile - \
    --error-logfile - \
    app:app
