# ==============
# LexChain API Dockerfile
# ==============
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy dependency list
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app /app/app

# Environment defaults (no secrets)
ENV LEXCHAIN_EMBED_MODEL="text-embedding-3-large"
ENV LEXCHAIN_INDEX_PATH="/app/backend/data/indexes/faiss_v1"
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
