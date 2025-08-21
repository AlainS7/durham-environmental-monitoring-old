########## Builder stage ##########
FROM python:3.11-slim AS builder

# Copy only requirement files for dependency resolution
WORKDIR /deps
COPY requirements.txt .

# Install uv (fast Python package manager) - pinned version and checksum verification
ENV UV_VERSION=0.8.4
ENV UV_URL=https://github.com/astral-sh/uv/releases/download/v${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz
ENV UV_SHA256=d43485d5531529c4a57bf9b504e9ac1609a4467d220a268c38464d83d6df08b6

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -L $UV_URL -o uv.tar.gz && \
    echo "$UV_SHA256  uv.tar.gz" | sha256sum -c - && \
    tar -xzf uv.tar.gz -C /usr/local/bin uv && \
    chmod +x /usr/local/bin/uv && \
    rm uv.tar.gz && \
    python -m pip install --upgrade pip setuptools wheel && \
    uv pip sync requirements.txt

########## Runtime stage ##########
FROM python:3.11-slim AS runtime

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for WeasyPrint (PDF generation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# Default command
CMD ["python", "src/data_collection/daily_data_collector.py"]