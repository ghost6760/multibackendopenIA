# Dockerfile multi-stage - CORREGIDO
FROM node:18-alpine AS frontend-builder

# Construir frontend React desde src/
WORKDIR /src
COPY src/package.json ./
# Copiar package-lock.json si existe
COPY src/package-lock.json* ./

# Cambiar npm ci por npm install
RUN npm install --production

COPY src/ .
RUN npm run build

# Stage 2: Backend Python
FROM python:3.11-slim AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend y archivos de configuración
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json ./

# Copiar el build del frontend
COPY --from=frontend-builder /frontend/build ./src/build

# Usuario no-root
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "wsgi:app"]
