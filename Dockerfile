# Stage 1: Build Frontend
FROM node:20-slim AS frontend

WORKDIR /app

# Configure npm mirror for faster install
RUN npm config set registry https://registry.npmmirror.com

# Install pnpm
RUN npm install -g pnpm

# Copy package files first to leverage cache
COPY ./myapp/package.json ./

# Install dependencies
RUN pnpm install

# Copy source code
COPY ./myapp .

# Build
RUN pnpm run build

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANSIBLE_HOST_KEY_CHECKING=False

# Install runtime dependencies
# openssh-client and sshpass are required for Ansible
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        sshpass \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Copy backend code
COPY ./app ./app

# Copy frontend build artifacts
COPY --from=frontend /app/dist /app/public

# Create necessary directories
RUN mkdir -p logs db /tmp/ansible_uploads

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
