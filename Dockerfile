# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app


# Copy requirements files into the container at /app
COPY requirements.txt .
COPY requirements-dev.txt .


# Install system dependencies for WeasyPrint (PDF generation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*


# Install uv (fast Python package manager) - pinned version and checksum verification
ENV UV_VERSION=0.8.4
ENV UV_URL=https://github.com/astral-sh/uv/releases/download/v${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz
ENV UV_SHA256=d43485d5531529c4a57bf9b504e9ac1609a4467d220a268c38464d83d6df08b6

RUN apt-get update && apt-get install -y curl ca-certificates && \
    curl -L $UV_URL -o uv.tar.gz && \
    echo "$UV_SHA256  uv.tar.gz" | sha256sum -c - && \
    tar -xzf uv.tar.gz -C /usr/local/bin uv && \
    chmod +x /usr/local/bin/uv && \
    rm uv.tar.gz && \
    uv pip sync requirements.txt && \
    uv pip sync requirements-dev.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Command to run the application
CMD ["python", "src/data_collection/daily_data_collector.py"]