FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY . /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
