FROM python:3.10-slim

# Set environment and working directory
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential curl

# Install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Use uvicorn CLI to run app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
