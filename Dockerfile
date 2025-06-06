# Build stage
FROM golang:1.20-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git make

# Set working directory
WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the server
RUN go build -o mcp-server-devpod main.go

# Runtime stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    curl \
    git \
    openssh-client \
    bash

# Install DevPod
RUN curl -L -o /tmp/devpod "https://github.com/loft-sh/devpod/releases/latest/download/devpod-linux-amd64" && \
    chmod +x /tmp/devpod && \
    mv /tmp/devpod /usr/local/bin/devpod

# Create non-root user
RUN addgroup -g 1000 mcp && \
    adduser -D -u 1000 -G mcp mcp

# Create necessary directories
RUN mkdir -p /home/mcp/.devpod && \
    chown -R mcp:mcp /home/mcp

# Copy the built binary
COPY --from=builder /build/mcp-server-devpod /usr/local/bin/mcp-server-devpod

# Set environment variables
ENV MCP_TRANSPORT=sse \
    MCP_ADDR=:8080 \
    DEVPOD_HOME=/home/mcp/.devpod \
    DEVPOD_PROVIDER=docker

# Switch to non-root user
USER mcp
WORKDIR /home/mcp

# Expose SSE port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - use shell form to expand environment variables
CMD mcp-server-devpod -transport=${MCP_TRANSPORT} -addr=${MCP_ADDR}