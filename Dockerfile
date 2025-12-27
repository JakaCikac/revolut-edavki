# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock* requirements.txt ./

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to not create virtual environment (we're in a container)
RUN poetry config virtualenvs.create false

# Install dependencies (without installing the project itself yet)
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 59855

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "59855"]
