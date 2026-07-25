# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create a virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project configuration and application code
COPY . .

# Install dependencies (not editable) into the virtual environment
RUN uv pip install .

# Stage 2: Runtime
FROM python:3.12-slim as runtime

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy the virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the rest of the application code (for migrations, etc.)
COPY --chown=appuser:appuser . .

# Create required storage directories and ensure appuser owns /app and all subdirectories
RUN mkdir -p storage/uploads storage/faiss_index storage/bm25_index && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Render dynamically injects the PORT environment variable. 
# We use the shell form of CMD to allow environment variable expansion.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"
