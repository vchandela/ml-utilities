FROM python:3.11-slim

# Install git and other tools needed for code operations
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models
COPY models.py .

# Copy worker source code (will be created in later steps)
COPY worker/ .

# Run worker
CMD ["python", "main.py"] 