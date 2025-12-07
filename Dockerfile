# Stage 1: Build Frontend
# Use node:20-slim as the base image for the frontend build stage
FROM node:20-slim AS frontend

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package configuration files first to leverage Docker cache
# Including .npmrc for project-specific configurations (e.g., legacy-peer-deps)
COPY ./myapp/package.json ./myapp/.npmrc ./

# Configure npm mirror and install dependencies
# We use registry.npmmirror.com for faster access in China
RUN npm config set registry https://registry.npmmirror.com && \
    pnpm install

# Copy the rest of the frontend source code
COPY ./myapp .

# Build the frontend application
RUN pnpm run build

# Stage 2: Runtime
# Use python:3.11-slim-bookworm for a smaller and secure runtime environment
FROM python:3.11-slim-bookworm

WORKDIR /app

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevent Python from writing .pyc files
# PYTHONUNBUFFERED: Ensure logs are output immediately
# PIP_NO_CACHE_DIR: Disable pip cache to save space
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANSIBLE_HOST_KEY_CHECKING=False

# Install runtime dependencies
# openssh-client and sshpass: Required for Ansible
# curl: Utility for network requests/health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        sshpass \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements file
COPY requirements.txt .

# Install Python dependencies
# Using Tsinghua mirror for faster installation
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Copy backend source code
COPY ./app ./app

# Copy frontend build artifacts from the build stage
COPY --from=frontend /app/dist /app/public

# Create necessary directories for logs, database, and uploads
RUN mkdir -p logs db /tmp/ansible_uploads

# Expose the application port
EXPOSE 3000

# Start the application using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
