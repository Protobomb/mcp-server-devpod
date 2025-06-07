# MCP Server for DevPod

An MCP (Model Context Protocol) server that provides an interface to [DevPod](https://devpod.sh/), enabling AI assistants to manage development environments programmatically.

## Features

- **Workspace Management**: Create, start, stop, and delete DevPod workspaces
- **Provider Management**: List and add DevPod providers
- **SSH Access**: Execute commands in workspaces via SSH
- **Status Monitoring**: Check the status of workspaces
- **Multiple Transports**: Supports STDIO, SSE (Server-Sent Events), and HTTP Streams transports

## Prerequisites

- [DevPod CLI](https://devpod.sh/docs/getting-started/install) installed and configured (included in Docker image)
- Go 1.19 or later (for building from source)
- Docker (for containerized deployment)

## Installation

### Option 1: From Source

```bash
git clone https://github.com/Protobomb/mcp-server-devpod.git
cd mcp-server-devpod
go build -o mcp-server-devpod
```

### Option 2: Using Docker

Run the server in a container with DevPod pre-installed:

```bash
# Using docker-compose
docker-compose up -d

# Or using docker directly
docker run -d \
  --name mcp-server-devpod \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v devpod-data:/home/mcp/.devpod \
  -e MCP_TRANSPORT=sse \
  -e DEVPOD_PROVIDER=docker \
  ghcr.io/protobomb/mcp-server-devpod:latest
```

The container includes:
- Pre-installed DevPod client
- SSE transport support for remote access
- Configurable environment variables
- Volume mounts for Docker socket and DevPod data persistence

## Usage

### STDIO Mode (Default)

```bash
./mcp-server-devpod
```

### SSE Mode

```bash
./mcp-server-devpod -transport=sse -addr=8080
```

### HTTP Streams Mode

```bash
./mcp-server-devpod -transport=http-streams -addr=8080
```

The HTTP Streams transport provides:
- **Full MCP Protocol Compliance**: Complete implementation per MCP specification
- **Session Management**: Secure session-based communication with UUID session IDs
- **Bidirectional Communication**: POST /mcp for client→server, SSE for server→client responses
- **Health Endpoint**: GET /health for service monitoring
- **CORS Support**: Full CORS headers for web client compatibility

### Environment Variables (Docker)

When running in Docker, you can configure the server using these environment variables:

- `MCP_TRANSPORT`: Transport type (`stdio`, `sse`, or `http-streams`, default: `sse`)
- `MCP_ADDR`: Address for SSE and HTTP Streams servers (default: `:8080`)
- `DEVPOD_HOME`: DevPod home directory (default: `/home/mcp/.devpod`)
- `DEVPOD_PROVIDER`: Default DevPod provider (default: `docker`)
- `DEVPOD_DOCKER_HOST`: Docker host for DevPod (default: `unix:///var/run/docker.sock`)

## Available Tools

The server exposes the following tools through the MCP protocol:

### Workspace Management

- **`devpod.listWorkspaces`**: List all DevPod workspaces
- **`devpod.createWorkspace`**: Create a new workspace
  - Parameters:
    - `name` (required): Workspace name
    - `source` (required): Repository URL or local path
    - `provider` (optional): Provider to use
    - `ide` (optional): IDE to use
- **`devpod.startWorkspace`**: Start a workspace
  - Parameters:
    - `name` (required): Workspace name
    - `ide` (optional): IDE to use
- **`devpod.stopWorkspace`**: Stop a workspace
  - Parameters:
    - `name` (required): Workspace name
- **`devpod.deleteWorkspace`**: Delete a workspace
  - Parameters:
    - `name` (required): Workspace name
    - `force` (optional): Force delete without confirmation
- **`devpod.status`**: Get workspace status
  - Parameters:
    - `name` (required): Workspace name

### Provider Management

- **`devpod.listProviders`**: List all available providers
- **`devpod.addProvider`**: Add a new provider
  - Parameters:
    - `name` (required): Provider name
    - `options` (optional): Provider-specific options

### Remote Access

- **`devpod.ssh`**: Execute commands in a workspace via SSH
  - Parameters:
    - `name` (required): Workspace name
    - `command` (optional): Command to execute

## Example Usage with MCP Client

### HTTP Streams Transport Usage

The HTTP Streams transport follows the MCP specification for HTTP-based communication:

```bash
# 1. Initialize session
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
  }'

# 2. Connect to SSE stream (use session ID from above response)
curl -N "http://localhost:8080/mcp?session=SESSION_ID"

# 3. Send messages (in another terminal)
curl -X POST "http://localhost:8080/mcp?session=SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'

# 4. Check health
curl http://localhost:8080/health
```

### Create a Workspace

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "devpod.createWorkspace",
  "params": {
    "name": "my-project",
    "source": "https://github.com/user/my-project.git",
    "provider": "docker",
    "ide": "vscode"
  }
}
```

### List Workspaces

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "devpod.listWorkspaces",
  "params": {}
}
```

### Execute Command in Workspace

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "devpod.ssh",
  "params": {
    "name": "my-project",
    "command": "npm install"
  }
}
```

## Integration with AI Assistants

This MCP server can be integrated with AI assistants that support the Model Context Protocol, such as:

- Claude Desktop
- Other MCP-compatible clients

### Configuration Example (Claude Desktop)

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "devpod": {
      "command": "/path/to/mcp-server-devpod",
      "args": []
    }
  }
}
```

## Development

### Building

```bash
go build -o mcp-server-devpod main.go
```

### Testing

```bash
go test ./...
```

## Architecture

The server is built using the [mcp-server-framework](https://github.com/Protobomb/mcp-server-framework) and implements handlers for DevPod CLI commands. It executes DevPod commands as subprocesses and returns the results through the MCP protocol.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [mcp-server-framework](https://github.com/Protobomb/mcp-server-framework)
- Interfaces with [DevPod](https://devpod.sh/) by Loft Labs