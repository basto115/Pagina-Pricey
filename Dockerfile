FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar Tesseract OCR y el idioma español
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del proyecto
COPY . .

# Recopilar archivos estáticos
RUN python manage.py collectstatic --no-input

# Puerto de Render
EXPOSE 10000

# Migraciones y servidor web
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000}"]