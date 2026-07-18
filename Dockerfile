# Use an official lightweight Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Prevents Python from buffering stdout/stderr (crucial for real-time Docker logging)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements.txt first to leverage Docker cache layers
COPY requirements.txt /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY src/ /app/src/
COPY sql/ /app/sql/
COPY dashboard/ /app/dashboard/
COPY docker-entrypoint.sh /app/

# Make sure entrypoint script is executable
RUN chmod +x /app/docker-entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
