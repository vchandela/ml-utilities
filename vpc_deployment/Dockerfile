# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY app/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container at /app
COPY app/ .

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables (optional but good practice)
ENV PYTHONUNBUFFERED 1
ENV APP_PORT 80

# Run app.py when the container launches
# Using --reload is useful for development, but for production,
# you'd typically use a production-ready server like gunicorn or uvicorn without --reload.
# For GKE deployment, this CMD will be overridden by your deployment configuration.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"] 