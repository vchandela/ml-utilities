FROM python:3.11-slim

WORKDIR /app

# Install Python deps (copy from bigquery_v2 subdir)
COPY bigquery_v2/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy both bigquery and bigquery_v2 modules
COPY bigquery/ bigquery/
COPY bigquery_v2/ bigquery_v2/

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app

# Default entrypoint
ENTRYPOINT ["python", "-m", "bigquery_v2.main"]
