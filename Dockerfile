# Use a Python base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for psycopg2 (PostgreSQL driver)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to take advantage of Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Environment variables (will be overridden by ECS at runtime)
ENV CHROMA_PATH=/mnt/chromadb
ENV AWS_DEFAULT_REGION=us-east-1
# Expose the port the FastAPI app will run on
EXPOSE 8000