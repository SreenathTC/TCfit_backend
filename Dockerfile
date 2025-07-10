FROM python:3.12.9-slim

# Set workdir
WORKDIR /app

# Install system dependencies (optional if needed)
RUN apt-get update && apt-get install -y gcc build-essential && \
    pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 5000

# Start the app
#CMD ["python", "app.py"]
# Run using Gunicorn with 300s timeout and 2 worker processes
#CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "app:app"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
