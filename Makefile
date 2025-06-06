.PHONY: build run run-sse test clean install build-all build-release docker docker-build docker-run docker-push docker-compose-up docker-compose-down fmt lint deps

# Binary name
BINARY_NAME=mcp-server-devpod

# Version (can be overridden)
VERSION?=dev

# Build flags
LDFLAGS=-ldflags="-s -w -X main.version=$(VERSION)"

# Build the binary
build:
	go build $(LDFLAGS) -o $(BINARY_NAME) main.go

# Run in STDIO mode
run: build
	./$(BINARY_NAME)

# Run in SSE mode
run-sse: build
	./$(BINARY_NAME) -transport=sse -addr=8080

# Run tests
test:
	go test -v ./...

# Clean build artifacts
clean:
	rm -f $(BINARY_NAME)
	go clean

# Install to system
install: build
	sudo cp $(BINARY_NAME) /usr/local/bin/

# Build for multiple platforms
build-all:
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-amd64 main.go
	GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-arm64 main.go
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-amd64 main.go
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-arm64 main.go
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-windows-amd64.exe main.go

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
	golangci-lint run

# Download dependencies
deps:
	go mod download
	go mod tidy