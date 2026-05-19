# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/models \
    TRANSFORMERS_CACHE=/opt/models \
    XDG_CACHE_HOME=/opt/models

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/models

COPY requirements.txt .

# Install CPU-only PyTorch first — avoids pulling 1 GB+ of CUDA packages.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# Pre-download NLP models so container startup is instant.
ARG SPACY_MODEL=en_core_web_lg
RUN python -m spacy download ${SPACY_MODEL}

RUN python -c "\
from transformers import pipeline; \
pipeline('text-classification', \
         model='protectai/deberta-v3-base-prompt-injection-v2', \
         device=-1)"

ARG TOXICITY_MODEL=original
RUN python -c "from detoxify import Detoxify; Detoxify('${TOXICITY_MODEL}')"

COPY . .

# Drop privileges. /home is created before the chown so .cache writes succeed.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin novisentinel \
 && chown -R novisentinel:novisentinel /app /home/novisentinel /opt/models
USER novisentinel

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
