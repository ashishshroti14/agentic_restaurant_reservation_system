# Use Python 3.9 as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port for Streamlit is 8501, but we'll use the PORT env var if provided
ENV PORT=8501

# Create a script to start Streamlit with the correct port
RUN echo '#!/bin/bash\n\
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0\n'\
> /app/start.sh && chmod +x /app/start.sh

# Expose the port that will be used
EXPOSE $PORT

# Command to run the Streamlit application using the dynamic port
CMD ["/app/start.sh"]
