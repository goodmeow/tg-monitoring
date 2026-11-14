FROM python:3.11-alpine

# .git is excluded from the build context, so record the version here.
ARG TG_MONITOR_VERSION=unknown
ENV TG_MONITOR_VERSION=${TG_MONITOR_VERSION}

WORKDIR /app

# Apply Alpine security upgrades available for the base image.
RUN apk upgrade --no-cache

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run the application
CMD ["python", "-m", "tgbot.main"]