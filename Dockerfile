FROM python:3.11-slim

# ── System dependencies (upgrade base packages for security patches) ──
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps (cached layer) ───────────────────────────
COPY requirements.txt .
# Install CPU torch first for reliable Docker builds without NVIDIA
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────
COPY . .

# ── Asset vault placeholders ─────────────────────────────
RUN python scripts/generate_assets.py || true

# ── Pre-warm ML models (CPU-safe) ────────────────────────
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
RUN python -c "\
from faster_whisper import WhisperModel; \
WhisperModel('medium', device='cpu', compute_type='int8'); \
print('whisper medium cached')" \
    && python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
print('embedder cached')" \
    && python -c "\
from ultralytics import YOLO; \
YOLO('yolo11n.pt'); \
print('yolo cached')"

# ── Create persistent dirs + non-root user ───────────────
RUN mkdir -p workspace output .cache assets/gifs assets/stickers assets/sfx \
    && groupadd --system --gid 1001 streamclip \
    && useradd --system --uid 1001 --gid streamclip --home-dir /app --shell /usr/sbin/nologin streamclip \
    && chown -R streamclip:streamclip /app

USER streamclip

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
