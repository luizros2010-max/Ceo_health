# Container image for cloud hosting (Render/Fly/Railway).
# Uses the prebuilt frontend (frontend/dist) committed in the repo, so no Node needed.
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; PyMuPDF ships manylinux wheels.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data (SQLite + uploads) lives on a mounted volume in production.
ENV DB_PATH=/data/ceo_health.db \
    DOCUMENTS_DIR=/data/documents \
    ICELAND_PHOTOS_DIR=/data/iceland_photos \
    REQUIRE_AUTH=true \
    PORT=8000

EXPOSE 8000

# Shell form so $PORT (set by the host) is expanded.
CMD uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port ${PORT:-8000}
