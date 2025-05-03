# Example Dockerfile for Infrash applications
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ssh \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Infrash
RUN pip install infrash

# Copy application code
COPY . .

# Expose port for web interface
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["python", "-m", "infrash"]

# Default command
CMD ["--help"]
