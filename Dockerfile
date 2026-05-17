FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Limitar threads de BLAS/OpenBLAS para reducir memoria en Starter (512 MB)
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

# Build tools para compilar pyswisseph (extensión C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY data ./data
COPY ["Motor academico/academic_assistant", "./academic_assistant"]
COPY ["Motor terapeutico/therapeutic_assistant", "./therapeutic_assistant"]

ENV PORT=8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
