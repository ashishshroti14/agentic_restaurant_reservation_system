# Use Python 3.9 as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PORT environment variable to 8080 for Cloud Run
ENV PORT=8080

# Create a startup script that uses the PORT environment variable
RUN echo '#!/bin/bash\n\
uvicorn main:app --host 0.0.0.0 --port $PORT\n'\
> /app/start.sh && chmod +x /app/start.sh

# Expose the port
EXPOSE $PORT

# Command to run the application
# Using app.main:app as the application import path with Uvicorn
CMD ["/app/start.sh"]
