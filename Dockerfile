FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch first — avoids pulling 1 GB+ of CUDA packages.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
