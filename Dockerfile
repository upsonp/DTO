FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    libproj-dev \
    proj-data \
    libgdal-dev \
    gcc \
    g++ \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash
ENV DISPLAY=:99

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true
RUN mkdir -p /app/logs && chmod 777 /app/logs

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]