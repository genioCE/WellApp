FROM python:3.11-slim

<<<<<<< HEAD
# Set working directory
WORKDIR /app

# Install system dependencies (for psycopg2-binary and general compatibility)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI using Uvicorn
=======
WORKDIR /app

COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PYTHONPATH=/app

>>>>>>> ceb7c6450b733fa1b750d1d5ec6570ee242452ab
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
