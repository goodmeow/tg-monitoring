FROM python:3.11-slim

# .git is excluded from the build context, so record the version here.
ARG TG_MONITOR_VERSION=unknown
ENV TG_MONITOR_VERSION=${TG_MONITOR_VERSION}

WORKDIR /app

# Apply Debian security updates available for the base image.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run the application
CMD ["python", "-m", "tgbot.main"]