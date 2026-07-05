# MedBrief AI — API container (FastAPI harness + agent)
#
# Build:  docker build -t medbrief-api .
# Run:    docker run -p 8000:8000 --env-file .env medbrief-api
#         (.env supplies GEMINI_API_KEY / GROQ_API_KEY — keys are NEVER baked
#          into the image; pass them at runtime only)
#
# Cloud Run deploy (from project root, keys via --set-env-vars or Secret Manager):
#   gcloud run deploy medbrief-api --source . --region us-central1 \
#     --set-secrets GEMINI_API_KEY=medbrief-gemini-key:latest
#
# To serve the ADK pipeline instead of the FastAPI harness, swap CMD for:
#   CMD ["adk", "api_server", "adk_app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + the data the loader/validator read
COPY src/ src/
COPY api/ api/
COPY adk_app/ adk_app/
COPY skills/ skills/
COPY mcp_server.py AGENTS.md ./
COPY sample_data/ sample_data/

# Non-root user — container runs unprivileged (security feature)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Cloud Run injects $PORT; default 8000 locally
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
