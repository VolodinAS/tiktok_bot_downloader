FROM python:3.12-slim

# === ENV ===
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Доверенные хосты для pip (только для разработки!)
    PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org"

# === Обновляем сертификаты и ставим необходимые утилиты ===
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    openssl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# === Пользователь ===
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# === Зависимости (отдельный слой для кэша) ===
COPY requirements.txt .
RUN pip install \
    --default-timeout=100 \
    --retries 5 \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# === Код приложения ===
COPY src/ ./src/

# === Папки и права ===
RUN mkdir -p videos/tik_tok logs && \
    chown -R appuser:appuser /home/appuser/app

USER appuser

# === Healthcheck ===
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "print('OK')" || exit 1

CMD ["python", "-m", "src.main"]