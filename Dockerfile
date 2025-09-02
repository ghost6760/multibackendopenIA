FROM node:18-alpine AS frontend-builder

WORKDIR /frontend
COPY src/package.json ./

# npm install sin lockfile - más confiable para este caso
RUN npm install

COPY src/ .
RUN npm run build

FROM python:3.11-slim AS backend

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json ./

COPY --from=frontend-builder /frontend/build ./src/build

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "wsgi:app"]
