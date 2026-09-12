# This is a Dockerfile for easy installation.
# It will setup 

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip bash curl

WORKDIR /app

# Upgrade Python packaging tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Download and install qarton from specific commit
RUN curl -L -o qarton.zip \
    https://gitlab.inria.fr/capsule/qarton/-/archive/4fdcf6961ad45104a460e5f54d587a6776a73461/qarton-4fdcf6961ad45104a460e5f54d587a6776a73461.zip && \
    unzip -q qarton.zip && \
    pip install ./qarton-4fdcf6961ad45104a460e5f54d587a6776a73461 && \
    rm -rf qarton.zip qarton-4fdcf6961ad45104a460e5f54d587a6776a73461

# Additional Python dependencies
RUN pip install --no-cache-dir matplotlib pytest

# Copy your project files last (better caching)
COPY . .

# Default shell entry
ENTRYPOINT ["/bin/bash"]

# Default command (interactive shell)
CMD []
