# ==========================================
# ETAPA 1: Builder (Instalacion de dependencias)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ==========================================
# ETAPA 2: Imagen Final (Runtime liviano)
# ==========================================
FROM python:3.11-slim

# Variables de entorno optimizadas con ruta completa a sbin y bin
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/appuser/.local/bin

# Instalar gosu y passwd (groupadd/useradd) para auto-reparar permisos
RUN apt-get update && apt-get install -y --no-install-recommends gosu passwd && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo sin privilegios
RUN (groupadd -g 1000 appgroup || addgroup --gid 1000 appgroup) && \
    (useradd -u 1000 -g appgroup -m appuser || adduser --disabled-password --gecos "" --uid 1000 --gid 1000 appuser)

WORKDIR /home/appuser/app

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup app/ ./app
COPY --chown=appuser:appgroup static/ ./static

RUN mkdir -p ./data ./config && chown -R appuser:appgroup /home/appuser/app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
