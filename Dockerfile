FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by PyMC / pytensor (C compiler).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables — override at runtime, never bake credentials here.
# LOVABLE_CREDITS controls the per-process credit budget.
# HEALTH_API_KEY is the Apple Health bridge API key.
ENV LOVABLE_CREDITS=100
ENV HEALTH_API_KEY=""
ENV LOG_LEVEL=INFO
ENV CORS_ORIGINS="*"
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
