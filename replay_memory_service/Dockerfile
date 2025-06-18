FROM python:3.11-slim

WORKDIR /app

# Install build tools and Rust for native dependencies like tokenizers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

# Set environment so Rust is usable during pip install
ENV PATH="/root/.cargo/bin:$PATH"

COPY . /app

RUN pip install --upgrade pip setuptools wheel

# Optional: force binary install (avoid building tokenizers from source)
# You can also preinstall tokenizers explicitly before the rest
RUN pip install tokenizers==0.13.3 --prefer-binary \
 && pip install -r requirements.txt --prefer-binary

ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
