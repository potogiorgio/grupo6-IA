FROM python:3.11-slim

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar el resto del código
COPY . /app

# Crear carpetas necesarias
RUN mkdir -p outputs data/tei data/pdfs data/intermediate

# Por defecto, no hace nada si no se especifica comando en docker-compose
CMD ["python", "--version"]
