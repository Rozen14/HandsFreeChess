# Use official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /workspace

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    portaudio19-dev \
    libasound2-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install torch first (biggest layer, changes least)
RUN pip install --no-cache-dir torch==2.5.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Default command
CMD ["bash"]
