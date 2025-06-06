# MCP Server for DevPod

An MCP (Model Context Protocol) server that provides an interface to [DevPod](https://devpod.sh/), enabling AI assistants to manage development environments programmatically.

## Features

- **Workspace Management**: Create, start, stop, and delete DevPod workspaces
- **Provider Management**: List and add DevPod providers
- **SSH Access**: Execute commands in workspaces via SSH
- **Status Monitoring**: Check the status of workspaces
- **Multiple Transports**: Supports both STDIO and SSE (Server-Sent Events) transports

## Prerequisites

- [DevPod CLI](https://devpod.sh/docs/getting-started/install) installed and configured
- Go 1.19 or later (for building from source)

## Installation

### From Source

```bash
git clone https://github.com/user/mcp-server-devpod.git
cd mcp-server-devpod
go build -o mcp-server-devpod
```

## Usage

### STDIO Mode (Default)

```bash
./mcp-server-devpod
```

### SSE Mode

```bash
./mcp-server-devpod -transport=sse -addr=:8080
```

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