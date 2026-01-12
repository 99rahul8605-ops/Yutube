FROM python:3.10-slim

WORKDIR /app

# Install system dependencies and build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    ffmpeg \
    aria2 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p downloads cookies

CMD ["python", "main.py"]
