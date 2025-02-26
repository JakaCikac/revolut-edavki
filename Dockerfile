# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the files needed for installation
COPY pyproject.toml poetry.lock ./
COPY revolut_edavki ./revolut_edavki

# Configure Poetry to create the virtualenv inside the project directory
RUN poetry config virtualenvs.in-project true

# Install dependencies
RUN poetry install --no-dev --no-interaction

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/revolut_edavki ./revolut_edavki
COPY server.py .
COPY .env.example .env

# Create uploads directory
RUN mkdir -p uploads && \
    chown -R nobody:nogroup uploads

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV HOST="0.0.0.0"
ENV PORT="55952"

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 55952

# Run the application
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "55952"]