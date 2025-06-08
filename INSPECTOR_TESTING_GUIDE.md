# MCP Inspector Testing Guide for DevPod Server

This guide shows you how to reproduce the complete DevPod workspace lifecycle testing using MCP Inspector.

## Prerequisites

1. **DevPod installed** (v0.6.15 or later)
2. **Docker provider configured** in DevPod
3. **MCP Inspector CLI** installed
4. **Go 1.21+** for building the server

## Quick Setup

### 1. Build the MCP Server
```bash
git clone https://github.com/Protobomb/mcp-server-devpod.git
cd mcp-server-devpod
go build -o mcp-server-devpod .
```

### 2. Install MCP Inspector
```bash
npm install -g @modelcontextprotocol/inspector-cli
```

### 3. Configure DevPod (if not already done)
```bash
# Ensure Docker provider is available
devpod provider list
# Should show docker provider

# If not present, add it:
devpod provider add docker
```

## Testing with MCP Inspector

### 1. Start MCP Inspector
```bash
mcp-inspector
```
This will start the Inspector UI on http://localhost:6274

### 2. Configure Connection in Inspector UI

In the Inspector web interface:

1. **Transport Type**: Select "STDIO"
2. **Command**: `./mcp-server-devpod` (or full path to binary)
3. **Arguments**: Leave empty
4. **Environment Variables**: Add `PWD` with your current directory path
5. Click **Connect**

### 3. Verify Connection

You should see:
- ✅ "Connected" status
- ✅ 11 tools listed (echo + 10 DevPod tools)
- ✅ Server logs showing successful initialization

## Complete DevPod Workflow Testing

### Step 1: List Providers
1. Click on `devpod.listProviders` tool
2. Click "Run Tool"
3. **Expected**: Shows available providers (docker, ssh, etc.)

### Step 2: List Workspaces
1. Click on `devpod.listWorkspaces` tool  
2. Click "Run Tool"
3. **Expected**: Empty array `[]` (no workspaces initially)

### Step 3: Create Workspace
1. Click on `devpod.createWorkspace` tool
2. Fill in parameters:
   - **ide**: `none`
   - **name**: `test-workspace`
   - **provider**: `docker`
   - **source**: `https://github.com/microsoft/vscode`
3. Click "Run Tool"
4. **Expected**: Success message with workspace creation logs

### Step 4: Check Workspace Status
1. Click on `devpod.status` tool
2. Fill in **name**: `test-workspace`
3. Click "Run Tool"
4. **Expected**: Status showing workspace is "Running"

### Step 5: SSH into Workspace
1. Click on `devpod.ssh` tool
2. Fill in parameters:
   - **name**: `test-workspace`
   - **command**: `ls -la`
3. Click "Run Tool"
4. **Expected**: Directory listing from inside the workspace

### Step 6: Stop Workspace
1. Click on `devpod.stopWorkspace` tool
2. Fill in **name**: `test-workspace`
3. Click "Run Tool"
4. **Expected**: Success message with stopping logs

### Step 7: Delete Workspace
1. Click on `devpod.deleteWorkspace` tool
2. Fill in **name**: `test-workspace`
3. Optionally check **force** for no confirmation
4. Click "Run Tool"
5. **Expected**: Success message with deletion logs

## Expected Results

After completing all steps, you should have:

✅ **Created** a DevPod workspace from a GitHub repository  
✅ **Checked status** of the running workspace  
✅ **SSH'd into** the workspace and executed commands  
✅ **Stopped** the workspace cleanly  
✅ **Deleted** the workspace completely  

All operations performed through the MCP protocol via Inspector UI!

## Troubleshooting

### Connection Issues
- Ensure `mcp-server-devpod` binary is built and executable
- Check that PWD environment variable is set correctly
- Verify DevPod is installed and in PATH

### DevPod Issues
- Ensure Docker is running and accessible
- Check DevPod provider configuration: `devpod provider list`
- Verify Docker provider is set as default or specify explicitly

### Tool Execution Issues
- Check server logs in Inspector UI for error details
- Ensure workspace names are unique
- Verify provider exists before creating workspaces

## Advanced Testing

### Test Other Providers
If you have SSH provider configured:
```bash
# Add SSH provider first
devpod provider add ssh --option HOST=user@hostname

# Then test with provider="ssh" in createWorkspace
```

### Test Different IDEs
Try different IDE options:
- `ide="vscode"`
- `ide="cursor"`
- `ide="vim"`
- `ide="none"` (headless)

### Test Different Sources
Try different repository sources:
- GitHub: `https://github.com/owner/repo`
- GitLab: `https://gitlab.com/owner/repo`
- Local: `/path/to/local/project`

## Transport Testing

The server supports 3 transport methods:

### STDIO (Default)
```bash
./mcp-server-devpod
```

### SSE (Server-Sent Events)
```bash
./mcp-server-devpod --transport sse --port 8082
```

### HTTP Streams
```bash
./mcp-server-devpod --transport http-streams --port 8083
```

Each transport can be tested with Inspector by changing the connection configuration.

## Success Criteria

A successful test run demonstrates:

1. **MCP Protocol Compliance**: All tools respond correctly via MCP
2. **DevPod Integration**: Full workspace lifecycle management
3. **Transport Flexibility**: Works across STDIO, SSE, and HTTP Streams
4. **Error Handling**: Graceful handling of invalid inputs
5. **Real Functionality**: Actual DevPod operations, not just mocks

This proves the MCP server provides a complete, functional interface to DevPod's capabilities!