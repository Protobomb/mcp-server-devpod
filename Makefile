.PHONY: build run run-sse test clean install

# Binary name
BINARY_NAME=mcp-server-devpod

# Build the binary
build:
	go build -o $(BINARY_NAME) main.go

# Run in STDIO mode
run: build
	./$(BINARY_NAME)

# Run in SSE mode
run-sse: build
	./$(BINARY_NAME) -transport=sse -addr=:8080

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
	GOOS=linux GOARCH=amd64 go build -o $(BINARY_NAME)-linux-amd64 main.go
	GOOS=darwin GOARCH=amd64 go build -o $(BINARY_NAME)-darwin-amd64 main.go
	GOOS=windows GOARCH=amd64 go build -o $(BINARY_NAME)-windows-amd64.exe main.go

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