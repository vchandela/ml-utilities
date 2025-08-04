# Dockerfile for the GCP Infrastructure Metrics Exporter service
# Builds a container image that can export GCP infrastructure metrics to Prometheus
# This service runs alongside the main application to provide monitoring capabilities

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container at /app
COPY main.py .

# Create non-root user for security
RUN useradd -m -u 1000 metrics && chown -R metrics:metrics /app
USER metrics

# Expose port 80
EXPOSE 80

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"] 