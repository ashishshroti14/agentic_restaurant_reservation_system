# Use Python 3.9 as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Streamlit
EXPOSE 8501

# Command to run the Streamlit application
# Use app.py as the entry point
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
