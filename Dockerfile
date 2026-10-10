FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/data/hf \
    TRANSFORMERS_CACHE=/data/hf \
    VERITY_DEVICE=cpu \
    VERITY_PORT=7860 \
    VERITY_PRELOAD_MODELS=true \
    VERITY_CORS_ORIGINS=*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY frontend ./frontend
COPY scripts ./scripts

# CPU-only wheels keep the image small and match the free CPU host.
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install .

# Pre-download the pretrained models so cold starts are reliable and the first
# request does not pay the download cost.
RUN python -c "from app.models_io import get_sentence_transformer, get_nli_components; \
get_sentence_transformer('BAAI/bge-small-en-v1.5'); \
get_nli_components('MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli')"

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
