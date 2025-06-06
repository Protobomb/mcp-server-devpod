# Example Usage

This document shows how to use the DevPod MCP server.

## Prerequisites

1. Install DevPod CLI:
```bash
# macOS
brew install loft-sh/tap/devpod

# Linux/Windows
curl -L -o devpod "https://github.com/loft-sh/devpod/releases/latest/download/devpod-linux-amd64"
chmod +x devpod
sudo mv devpod /usr/local/bin/devpod

# Or download from https://github.com/loft-sh/devpod/releases
```

2. Build the MCP server:
```bash
make build
```

## Running the Server

### Standalone (STDIO mode)
```bash
./mcp-server-devpod
```

### SSE mode
```bash
./mcp-server-devpod -transport=sse -addr=:8080
```

## Integration with Claude Desktop

1. Add to your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

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

2. Restart Claude Desktop

## Example Commands

Once integrated with Claude Desktop, you can ask Claude to:

- "List my DevPod workspaces"
- "Create a new DevPod workspace called 'my-project' from https://github.com/user/repo"
- "Start the 'my-project' workspace"
- "Run 'npm install' in the 'my-project' workspace"
- "Stop the 'my-project' workspace"
- "Delete the 'my-project' workspace"

## Testing with the Test Client

```bash
# Build the test client
go build -o test_client test_client.go

# Run the test
./test_client
```

## Manual Testing with curl (SSE mode)

1. Start the server in SSE mode:
```bash
./mcp-server-devpod -transport=sse -addr=:8080
```

2. Initialize connection:
```bash
curl -X POST http://localhost:8080/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "0.1.0",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

3. List tools:
```bash
curl -X POST http://localhost:8080/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

4. List workspaces:
```bash
curl -X POST http://localhost:8080/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "devpod.listWorkspaces",
      "arguments": {}
    }
  }'
```

## Troubleshooting

### DevPod not found
Make sure DevPod is installed and available in your PATH:
```bash
which devpod
devpod version
```

### Permission denied
Make sure the server binary is executable:
```bash
chmod +x mcp-server-devpod
```

### Connection issues
Check that the server is running:
```bash
ps aux | grep mcp-server-devpod
```

For SSE mode, check that the port is not in use:
```bash
lsof -i :8080
```