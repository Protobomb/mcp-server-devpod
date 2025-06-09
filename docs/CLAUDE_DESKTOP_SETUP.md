# Claude Desktop Setup Guide

This guide explains how to set up the DevPod MCP server with Claude Desktop.

## Prerequisites

1. **Claude Desktop**: Download and install from [Claude Desktop](https://claude.ai/desktop)
2. **DevPod**: Install DevPod from [devpod.sh](https://devpod.sh/) (optional - tools will show helpful errors if not available)

## Installation

### Step 1: Download the Binary

Download the latest `mcp-server-devpod` binary from the [releases page](https://github.com/Protobomb/mcp-server-devpod/releases).

### Step 2: Install the Binary

Place the binary in a directory in your PATH:

```bash
# macOS/Linux
sudo mv mcp-server-devpod /usr/local/bin/
sudo chmod +x /usr/local/bin/mcp-server-devpod

# Or in your home directory
mkdir -p ~/bin
mv mcp-server-devpod ~/bin/
chmod +x ~/bin/mcp-server-devpod
```

### Step 3: Configure Claude Desktop

Add the following configuration to your Claude Desktop config file:

**Config file locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "devpod": {
      "command": "/usr/local/bin/mcp-server-devpod",
      "args": ["--transport", "stdio"],
      "env": {}
    }
  }
}
```

**Note**: Update the `command` path to match where you installed the binary.

### Step 4: Restart Claude Desktop

Close and restart Claude Desktop for the changes to take effect.

## Verification

After restarting Claude Desktop, you should see the DevPod tools available in the interface. You can test by asking Claude to:

- "List my DevPod workspaces"
- "Show me the available DevPod tools"

## Available Tools

The MCP server provides the following DevPod tools:

1. **devpod_listWorkspaces** - List all DevPod workspaces
2. **devpod_status** - Get the status of a specific workspace
3. **devpod_createWorkspace** - Create a new workspace
4. **devpod_deleteWorkspace** - Delete a workspace
5. **devpod_startWorkspace** - Start a workspace
6. **devpod_stopWorkspace** - Stop a workspace
7. **devpod_listProviders** - List available providers
8. **devpod_addProvider** - Add a new provider
9. **devpod_removeProvider** - Remove a provider
10. **devpod_ssh** - SSH into a workspace

## Troubleshooting

### Server Not Starting

If the server doesn't start, check:

1. **Binary permissions**: Ensure the binary is executable
2. **Path**: Verify the command path in the config is correct
3. **Logs**: Check Claude Desktop logs for error messages

### DevPod Not Available

If DevPod is not installed, the tools will return helpful error messages explaining how to install DevPod. The server will still start and function - it just won't be able to execute DevPod commands.

### Connection Issues

If you see connection errors:

1. Restart Claude Desktop
2. Check the config file syntax (must be valid JSON)
3. Verify the binary path is correct and accessible

## Advanced Configuration

### Custom Environment Variables

You can add environment variables to the configuration:

```json
{
  "mcpServers": {
    "devpod": {
      "command": "/usr/local/bin/mcp-server-devpod",
      "args": ["--transport", "stdio"],
      "env": {
        "DEVPOD_CONFIG": "/custom/path/to/config"
      }
    }
  }
}
```

### Multiple Servers

You can run multiple MCP servers alongside DevPod:

```json
{
  "mcpServers": {
    "devpod": {
      "command": "/usr/local/bin/mcp-server-devpod",
      "args": ["--transport", "stdio"],
      "env": {}
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
      "env": {}
    }
  }
}
```

## Support

For issues and questions:

- **GitHub Issues**: [mcp-server-devpod issues](https://github.com/Protobomb/mcp-server-devpod/issues)
- **DevPod Documentation**: [devpod.sh/docs](https://devpod.sh/docs)
- **MCP Documentation**: [Model Context Protocol](https://modelcontextprotocol.io/)