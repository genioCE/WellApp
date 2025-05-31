FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

<<<<<<< HEAD
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
=======
RUN apt-get update && apt-get install -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*
>>>>>>> ceb7c6450b733fa1b750d1d5ec6570ee242452ab

COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

<<<<<<< HEAD
EXPOSE 8000
=======
COPY . /app/

RUN mkdir -p visualizations
>>>>>>> ceb7c6450b733fa1b750d1d5ec6570ee242452ab

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
