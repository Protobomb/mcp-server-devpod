.PHONY: build run run-sse run-http-streams test test-coverage test-integration-stdio test-integration-sse test-integration-http-streams test-integration-devpod test-integration-all test-integration-all-parallel test-inspector-cli test-inspector-ui test-all clean install build-all build-release docker docker-build docker-run docker-push docker-compose-up docker-compose-down fmt lint deps coverage security benchmark check ci release help

# Binary name
BINARY_NAME=mcp-server-devpod

# Version (can be overridden)
VERSION?=$(shell git describe --tags --always --dirty)
BUILD_TIME=$(shell date -u '+%Y-%m-%d_%H:%M:%S')

# Build flags
LDFLAGS=-ldflags="-s -w -X main.version=$(VERSION) -X main.buildTime=$(BUILD_TIME)"

# Build the binary
build:
	go build $(LDFLAGS) -o $(BINARY_NAME) main.go

# Run in STDIO mode
run: build
	./$(BINARY_NAME)

# Run in SSE mode
run-sse: build
	./$(BINARY_NAME) -transport sse -addr 8080

# Run in HTTP Streams mode
run-http-streams: build
	./$(BINARY_NAME) -transport http-streams -addr 8080

# Run tests
test:
	go test -v -race ./...

# Run tests with coverage
test-coverage:
	go test -v -race -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

# Generate coverage report
coverage: test-coverage
	go tool cover -func=coverage.out

# Clean build artifacts
clean:
	rm -f $(BINARY_NAME)
	rm -rf dist/
	rm -f coverage.out coverage.html
	go clean

# Install to system
install: build
	sudo cp $(BINARY_NAME) /usr/local/bin/

# Build for multiple platforms
build-all:
	@echo "Building for multiple platforms..."
	@mkdir -p dist
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o dist/$(BINARY_NAME)-linux-amd64 main.go
	GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o dist/$(BINARY_NAME)-linux-arm64 main.go
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o dist/$(BINARY_NAME)-darwin-amd64 main.go
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o dist/$(BINARY_NAME)-darwin-arm64 main.go
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o dist/$(BINARY_NAME)-windows-amd64.exe main.go

# Build release with archives
build-release:
	./scripts/build-release.sh $(VERSION)

# Docker commands
DOCKER_IMAGE=ghcr.io/protobomb/mcp-server-devpod

docker: docker-build

docker-build:
	docker build -t $(DOCKER_IMAGE):$(VERSION) .

docker-run:
	docker run -d \
		--name mcp-server-devpod \
		-p 8080:8080 \
		-v /var/run/docker.sock:/var/run/docker.sock:ro \
		-v devpod-data:/home/mcp/.devpod \
		-e MCP_TRANSPORT=sse \
		-e DEVPOD_PROVIDER=docker \
		$(DOCKER_IMAGE):$(VERSION)

docker-push: docker-build
	docker push $(DOCKER_IMAGE):$(VERSION)

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

# Format code
fmt:
	go fmt ./...

# Run linter
lint:
	@which golangci-lint > /dev/null || (echo "Installing golangci-lint..." && go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.50.1)
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run; \
	else \
		$(shell go env GOPATH)/bin/golangci-lint run; \
	fi

# Download dependencies
deps:
	go mod download
	go mod tidy

# DevPod-specific integration tests
test-integration-stdio: build
	@echo "Running STDIO integration tests..."
	python3 scripts/test_stdio_integration.py --server-binary=./$(BINARY_NAME)

test-integration-sse: build
	@echo "Running SSE integration tests..."
	python3 scripts/test_sse_integration.py --port 8081

test-integration-http-streams: build
	@echo "Running HTTP Streams integration tests..."
	python3 scripts/test_http_streams_integration.py --port 8082

test-integration-devpod: build
	@echo "Running DevPod functionality tests..."
	python3 test_devpod_mcp.py

test-devpod-tools: build
	@echo "Running comprehensive DevPod tool tests..."
	python3 scripts/test_devpod_tools.py --transport=stdio
	python3 scripts/test_devpod_tools.py --transport=sse --port 8081
	python3 scripts/test_devpod_tools.py --transport=http-streams --port 8082

test-integration-all: build
	@echo "Running all transport integration tests..."
	python3 scripts/test_all_transports.py --transport=all

test-integration-all-parallel: build
	@echo "Running all transport integration tests in parallel..."
	python3 scripts/test_all_transports.py --transport=all --parallel

test-all: test test-integration-all

# MCP Inspector testing
test-inspector-cli: build
	@echo "Testing with MCP Inspector CLI..."
	@echo "Note: This requires @modelcontextprotocol/inspector to be installed"
	npx @modelcontextprotocol/inspector --cli ./$(BINARY_NAME) --transport stdio --method tools/list

test-inspector-ui: build
	@echo "Testing with MCP Inspector UI..."
	@echo "Note: This requires @modelcontextprotocol/inspector to be installed"
	@echo "This will open a web interface for testing"
	npx @modelcontextprotocol/inspector ./$(BINARY_NAME) --transport stdio

# Additional development tools
benchmark:
	go test -bench=. -benchmem ./...

security:
	@which gosec > /dev/null || (echo "Installing gosec..." && go install github.com/securecodewarrior/gosec/v2/cmd/gosec@latest)
	gosec ./...

vet:
	go vet ./...

check: deps fmt vet lint test-all

ci: check build

release: clean check build-all

help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Build targets:'
	@echo '  build                    Build the server binary'
	@echo '  build-all               Build for all platforms'
	@echo '  clean                   Clean build artifacts'
	@echo ''
	@echo 'Run targets:'
	@echo '  run                     Run in STDIO mode'
	@echo '  run-sse                 Run in SSE mode'
	@echo '  run-http-streams        Run in HTTP Streams mode'
	@echo ''
	@echo 'Test targets:'
	@echo '  test                    Run unit tests'
	@echo '  test-coverage           Run tests with coverage'
	@echo '  test-integration-stdio  Test STDIO transport'
	@echo '  test-integration-sse    Test SSE transport'
	@echo '  test-integration-http-streams  Test HTTP Streams transport'
	@echo '  test-integration-devpod Test DevPod functionality'
	@echo '  test-integration-all    Test all transports'
	@echo '  test-integration-all-parallel  Test all transports in parallel'
	@echo '  test-inspector-cli      Test with MCP Inspector CLI'
	@echo '  test-inspector-ui       Test with MCP Inspector UI'
	@echo '  test-all                Run all tests'
	@echo ''
	@echo 'Quality targets:'
	@echo '  fmt                     Format code'
	@echo '  lint                    Run linter'
	@echo '  vet                     Run go vet'
	@echo '  security                Run security scan'
	@echo '  benchmark               Run benchmarks'
	@echo '  coverage                Generate coverage report'
	@echo ''
	@echo 'Docker targets:'
	@echo '  docker-build            Build Docker image'
	@echo '  docker-run              Run Docker container'
	@echo '  docker-push             Push Docker image'
	@echo ''
	@echo 'Meta targets:'
	@echo '  check                   Run all quality checks'
	@echo '  ci                      Run CI pipeline locally'
	@echo '  release                 Prepare release'
	@echo '  help                    Show this help'

# Default target
.DEFAULT_GOAL := help