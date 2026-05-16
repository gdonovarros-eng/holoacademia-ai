FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY data ./data
COPY ["Motor academico/academic_assistant", "./academic_assistant"]
COPY ["Motor terapeutico/therapeutic_assistant", "./therapeutic_assistant"]

ENV PORT=8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
