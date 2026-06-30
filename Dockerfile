FROM python:3.11-slim

# ── System dependencies ──────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# ── Create persistent dirs ───────────────────────────────
RUN mkdir -p workspace output .cache assets/gifs assets/stickers assets/sfx

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
