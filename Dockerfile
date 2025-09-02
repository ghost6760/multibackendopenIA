# Dockerfile multi-stage para Railway
FROM node:18-alpine AS frontend-builder

# Construir frontend React
WORKDIR /src
COPY src/package*.json ./
RUN npm ci --only=production

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

# Instalar dependencias Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY backend/app/ ./app/
COPY backend/app.py backend/wsgi.py ./
COPY companies_config.json extended_companies_config.json ./

# Copiar el build del frontend desde el stage anterior
COPY --from=frontend-builder /src/build ./src/build

# Usuario no-root
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "wsgi:app"]
