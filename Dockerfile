# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies for WeasyPrint (PDF generation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -r requirements-dev.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Command to run the application
CMD ["python", "src/data_collection/daily_data_collector.py"]