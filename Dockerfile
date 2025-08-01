# Dockerfile optimizado para Railway con solución OpenBLAS
FROM python:3.11-slim

# Configurar variables de entorno CRÍTICAS para OpenBLAS
ENV OPENBLAS_NUM_THREADS=1 \
    GOTO_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Instalar solo dependencias esenciales
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para mejor caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Usar usuario no-root
RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE $PORT

# Usar Gunicorn con configuración optimizada
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --worker-class gthread app:app"]
