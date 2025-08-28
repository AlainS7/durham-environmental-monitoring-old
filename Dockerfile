########## Builder stage ##########
FROM python:3.11-slim-bookworm AS builder

# Copy only requirement files for dependency resolution
WORKDIR /deps
COPY requirements.txt .

# Install uv (fast Python package manager) - pinned version and checksum verification
ENV UV_VERSION=0.8.13
ENV UV_URL=https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz
ENV UV_SHA256=8ca3db7b2a3199171cfc0870be1f819cb853ddcec29a5fa28dae30278922b7ba

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates; \
    curl -L "$UV_URL" -o uv.tar.gz; \
    echo "$UV_SHA256  uv.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/uv-extract; \
    tar -xzf uv.tar.gz -C /tmp/uv-extract; \
    # Find the uv binary anywhere inside the extracted tree
    UV_BIN_PATH="$(find /tmp/uv-extract -type f -name uv -perm -u+x | head -n1)"; \
    if [ -z "$UV_BIN_PATH" ]; then echo 'uv binary not found in archive' >&2; exit 1; fi; \
    mv "$UV_BIN_PATH" /usr/local/bin/uv; \
    chmod +x /usr/local/bin/uv; \
    rm -rf uv.tar.gz /tmp/uv-extract; \
    python -m pip install --upgrade pip setuptools wheel; \
    # Install dependencies into the system environment (no virtualenv inside container)
    uv pip sync requirements.txt --system

########## Runtime stage ##########
FROM python:3.11-slim-bookworm AS runtime

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for WeasyPrint (PDF generation)
## NOTE:
##  - Some Debian testing images (trixie/sid) briefly renamed/obsoleted libgdk-pixbuf2.0-0 in favor of split packages.
##  - We pin to the bookworm variant for stability and keep the original package list.
##  - If the package name changes upstream again, add an OR fallback.
RUN set -eux; \
        apt-get update; \
        # Try primary package list; if gdk-pixbuf package name changes, attempt a fallback.
        if ! apt-get install -y --no-install-recommends \
                libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info; then \
                echo 'Primary install failed, attempting fallback for gdk-pixbuf package name' >&2; \
                apt-get install -y --no-install-recommends \
                    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-xlib-2.0-0 libffi-dev shared-mime-info; \
        fi; \
        rm -rf /var/lib/apt/lists/*

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# Ensure application root is on Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "src/data_collection/daily_data_collector.py"]