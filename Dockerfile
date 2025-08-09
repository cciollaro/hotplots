# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpython3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the project's dependency file
COPY pyproject.toml .

# Install any needed packages specified in pyproject.toml
RUN pip install --no-cache-dir .[dev]

# Copy the entire project
COPY . .

# Since this Dockerfile is for running tests, we don't need a default CMD.
# The test runner will execute the necessary commands.
