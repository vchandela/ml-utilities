FROM python:3.12-slim

# Base OS deps
RUN apt-get update \
    && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/*

# Node.js (for CLI packages)
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs

# Install Gemini, Claude, Codex CLIs (verified packages)
RUN npm install -g \
      @google/gemini-cli \
      @anthropic-ai/claude-code \
      @openai/codex

WORKDIR /app

# Copy requirements and install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models
COPY models.py .

# Copy worker source code
COPY worker/ .

# Run worker
CMD ["python", "main.py"] 