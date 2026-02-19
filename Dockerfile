# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv via pip
RUN pip install uv

# Copy project definition
COPY pyproject.toml ./

# Install dependencies (frozen, no dev deps)
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Render sets $PORT dynamically)
# Default to 8080 if not set
ENV PORT=8080

# Run the application
# Use shell form to allow variable expansion for $PORT
CMD ["sh", "-c", "uv run solara run app.py --host 0.0.0.0 --port $PORT"]
