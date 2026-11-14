FROM python:3.11-slim

# .git is excluded from the build context, so record the version here.
ARG TG_MONITOR_VERSION=unknown
ENV TG_MONITOR_VERSION=${TG_MONITOR_VERSION}

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run the application
CMD ["python", "-m", "tgbot.main"]