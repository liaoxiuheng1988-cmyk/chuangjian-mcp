FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy everything
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn>=0.23.0 \
    pydantic>=2.0.0 \
    httpx>=0.24.0 \
    psycopg2-binary \
    sentence-transformers \
    flask

EXPOSE 8080

# Start the MCP server
CMD ["uvicorn", "mcp_server.startup_opportunity_discovery:app", "--host", "0.0.0.0", "--port", "8080"]
