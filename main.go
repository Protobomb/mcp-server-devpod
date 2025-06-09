package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"

	"github.com/protobomb/mcp-server-framework/pkg/mcp"
	"github.com/protobomb/mcp-server-framework/pkg/transport"
)

// version is set during build time via ldflags
var version = "dev"

// DevPodWorkspace represents a DevPod workspace
type DevPodWorkspace struct {
	Name     string `json:"name"`
	Provider string `json:"provider"`
	Status   string `json:"status"`
	IDE      string `json:"ide,omitempty"`
}

// DevPodProvider represents a DevPod provider
type DevPodProvider struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Version     string `json:"version"`
	Default     bool   `json:"default"`
}

func main() {
	// Add panic recovery to catch any crashes
	defer func() {
		if r := recover(); r != nil {
			log.Printf("PANIC: Server crashed with error: %v", r)
			fmt.Fprintf(os.Stderr, "PANIC: Server crashed with error: %v\n", r)
			os.Exit(1)
		}
	}()

	var (
		transportType = flag.String("transport", "stdio", "Transport type: stdio, sse, or http-streams")
		addr          = flag.String("addr", "8080", "Port for SSE and HTTP Streams transports")
		showVersion   = flag.Bool("version", false, "Show version information")
	)
	flag.Parse()

	if *showVersion {
		fmt.Printf("mcp-server-devpod version %s\n", version)
		return
	}

	log.Printf("Starting DevPod MCP server with transport: %s", *transportType)
	fmt.Fprintf(os.Stderr, "Starting DevPod MCP server with transport: %s\n", *transportType)

	// Format address for SSE and HTTP Streams transports
	var formattedAddr string
	if *transportType == "sse" || *transportType == "http-streams" {
		// If addr doesn't start with ":", add it
		if !strings.HasPrefix(*addr, ":") {
			formattedAddr = ":" + *addr
		} else {
			formattedAddr = *addr
		}
	}

	// Create transport
	log.Printf("Creating transport: %s", *transportType)
	fmt.Fprintf(os.Stderr, "Creating transport: %s\n", *transportType)
	var t mcp.Transport
	switch *transportType {
	case "stdio":
		t = transport.NewSTDIOTransport()
	case "sse":
		t = transport.NewSSETransport(formattedAddr)
	case "http-streams":
		t = transport.NewHTTPStreamsTransport(formattedAddr)
	default:
		log.Fatalf("Unknown transport type: %s (supported: stdio, sse, http-streams)", *transportType)
	}

	// Create server
	log.Printf("Creating MCP server")
	fmt.Fprintf(os.Stderr, "Creating MCP server\n")
	server := mcp.NewServer(t)

	// Setup context with cancellation
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("Shutting down DevPod MCP server...")
		cancel()
	}()

	// Register MCP protocol handlers BEFORE starting the server (to prevent override)
	log.Printf("Registering MCP protocol handlers")
	fmt.Fprintf(os.Stderr, "Registering MCP protocol handlers\n")
	registerMCPHandlers(server)

	// Register DevPod handlers BEFORE starting the server
	log.Printf("Registering DevPod handlers")
	fmt.Fprintf(os.Stderr, "Registering DevPod handlers\n")
	registerDevPodHandlers(server)

	// Set up message handler for HTTP-based transports
	log.Printf("Setting up message handler")
	fmt.Fprintf(os.Stderr, "Setting up message handler\n")
	setupMessageHandler(server, t)

	// Add debug output to stderr for Claude Desktop
	fmt.Fprintf(os.Stderr, "DevPod MCP server initializing with %s transport\n", *transportType)

	// Start server (default handlers won't override existing ones)
	log.Printf("About to start server...")
	fmt.Fprintf(os.Stderr, "About to start server...\n")
	if err := server.Start(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start server: %v\n", err)
		log.Printf("Failed to start server: %v", err)
		log.Fatalf("Failed to start server: %v", err)
	}

	fmt.Fprintf(os.Stderr, "DevPod MCP server started with %s transport\n", *transportType)
	log.Printf("DevPod MCP server started with %s transport", *transportType)
	if *transportType == "sse" {
		log.Printf("Starting SSE server on %s", formattedAddr)
		log.Printf("Listening on %s", *addr)
	} else if *transportType == "http-streams" {
		log.Printf("Starting HTTP Streams server on %s", formattedAddr)
		log.Printf("Listening on %s", *addr)
		log.Printf("Endpoints: /mcp (POST/GET), /health (GET)")
	}

	// Wait for context cancellation
	fmt.Fprintf(os.Stderr, "DevPod MCP server waiting for shutdown signal...\n")
	<-ctx.Done()
	fmt.Fprintf(os.Stderr, "DevPod MCP server received shutdown signal, cleaning up...\n")

	// Cleanup
	if err := server.Stop(); err != nil {
		fmt.Fprintf(os.Stderr, "Error stopping server: %v\n", err)
		log.Printf("Error stopping server: %v", err)
	}

	if err := server.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "Error closing server: %v\n", err)
		log.Printf("Error closing server: %v", err)
	}

	fmt.Fprintf(os.Stderr, "DevPod MCP server stopped\n")
	log.Println("Server stopped")
}

func registerMCPHandlers(server *mcp.Server) {
	log.Printf("Registering prompts/list handler")
	fmt.Fprintf(os.Stderr, "Registering prompts/list handler\n")
	// Register prompts/list handler (required by Claude Desktop)
	server.RegisterHandler("prompts/list", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		log.Printf("prompts/list called")
		fmt.Fprintf(os.Stderr, "prompts/list called\n")
		// Return empty prompts list since we don't provide any prompts
		return map[string]interface{}{
			"prompts": []interface{}{},
		}, nil
	})

	log.Printf("Registering resources/list handler")
	fmt.Fprintf(os.Stderr, "Registering resources/list handler\n")
	// Register resources/list handler (optional but good practice)
	server.RegisterHandler("resources/list", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		log.Printf("resources/list called")
		fmt.Fprintf(os.Stderr, "resources/list called\n")
		// Return empty resources list since we don't provide any resources
		return map[string]interface{}{
			"resources": []interface{}{},
		}, nil
	})

	log.Printf("Registering tools/list handler")
	fmt.Fprintf(os.Stderr, "Registering tools/list handler\n")
	// Override the default tools/list handler to include our DevPod tools
	server.RegisterHandler("tools/list", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		log.Printf("tools/list called")
		fmt.Fprintf(os.Stderr, "tools/list called\n")
		tools := []map[string]interface{}{
			// Echo tool (from framework)
			{
				"name":        "echo",
				"description": "Echo back the provided message",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"message": map[string]interface{}{
							"type":        "string",
							"description": "The message to echo back",
						},
					},
					"required": []string{"message"},
				},
			},
			// DevPod tools
			{
				"name":        "devpod_listWorkspaces",
				"description": "List all DevPod workspaces",
				"inputSchema": map[string]interface{}{
					"type":       "object",
					"properties": map[string]interface{}{},
				},
			},
			{
				"name":        "devpod_status",
				"description": "Get the status of a specific DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod_createWorkspace",
				"description": "Create a new DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
						"source": map[string]interface{}{
							"type":        "string",
							"description": "The source repository or path",
						},
						"provider": map[string]interface{}{
							"type":        "string",
							"description": "The provider to use (optional)",
						},
						"ide": map[string]interface{}{
							"type":        "string",
							"description": "The IDE to use (optional)",
						},
					},
					"required": []string{"name", "source"},
				},
			},
			{
				"name":        "devpod_startWorkspace",
				"description": "Start a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
						"ide": map[string]interface{}{
							"type":        "string",
							"description": "The IDE to use (optional)",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod_stopWorkspace",
				"description": "Stop a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod_deleteWorkspace",
				"description": "Delete a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
						"force": map[string]interface{}{
							"type":        "boolean",
							"description": "Force deletion without confirmation",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod_ssh",
				"description": "SSH into a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the workspace",
						},
						"command": map[string]interface{}{
							"type":        "string",
							"description": "Command to execute (optional)",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod_listProviders",
				"description": "List all DevPod providers",
				"inputSchema": map[string]interface{}{
					"type":       "object",
					"properties": map[string]interface{}{},
				},
			},
			{
				"name":        "devpod_addProvider",
				"description": "Add a new DevPod provider",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "The name of the provider",
						},
						"options": map[string]interface{}{
							"type":        "object",
							"description": "Provider-specific options",
						},
					},
					"required": []string{"name"},
				},
			},
		}

		return map[string]interface{}{
			"tools": tools,
		}, nil
	})
}

func registerDevPodHandlers(server *mcp.Server) {
	log.Printf("Registering DevPod handlers")
	fmt.Fprintf(os.Stderr, "Registering DevPod handlers\n")
	
	// List workspaces
	log.Printf("Registering devpod_listWorkspaces handler")
	fmt.Fprintf(os.Stderr, "Registering devpod_listWorkspaces handler\n")
	server.RegisterHandler("devpod_listWorkspaces", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		cmd := exec.CommandContext(ctx, "devpod", "list", "--output", "json")
		output, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("failed to list workspaces: %w", err)
		}

		var workspaces []DevPodWorkspace
		if err := json.Unmarshal(output, &workspaces); err != nil {
			// If JSON parsing fails, try to parse the text output
			return parseTextWorkspaceList(string(output)), nil
		}

		return map[string]interface{}{
			"workspaces": workspaces,
		}, nil
	})

	// Create workspace
	server.RegisterHandler("devpod_createWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var createParams struct {
			Name     string `json:"name"`
			Source   string `json:"source"`
			Provider string `json:"provider,omitempty"`
			IDE      string `json:"ide,omitempty"`
		}

		if err := json.Unmarshal(params, &createParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid create workspace parameters")
		}

		if createParams.Name == "" || createParams.Source == "" {
			return nil, mcp.NewInvalidParamsError("Name and source are required")
		}

		args := []string{"up", createParams.Source, "--id", createParams.Name}
		if createParams.Provider != "" {
			args = append(args, "--provider", createParams.Provider)
		}
		if createParams.IDE != "" {
			args = append(args, "--ide", createParams.IDE)
		}

		cmd := exec.CommandContext(ctx, "devpod", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to create workspace: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    createParams.Name,
			"message": "Workspace created successfully",
			"output":  string(output),
		}, nil
	})

	// Start workspace
	server.RegisterHandler("devpod_startWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var startParams struct {
			Name string `json:"name"`
			IDE  string `json:"ide,omitempty"`
		}

		if err := json.Unmarshal(params, &startParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid start workspace parameters")
		}

		if startParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Workspace name is required")
		}

		args := []string{"up", startParams.Name}
		if startParams.IDE != "" {
			args = append(args, "--ide", startParams.IDE)
		}

		cmd := exec.CommandContext(ctx, "devpod", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to start workspace: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    startParams.Name,
			"message": "Workspace started successfully",
			"output":  string(output),
		}, nil
	})

	// Stop workspace
	server.RegisterHandler("devpod_stopWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var stopParams struct {
			Name string `json:"name"`
		}

		if err := json.Unmarshal(params, &stopParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid stop workspace parameters")
		}

		if stopParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Workspace name is required")
		}

		cmd := exec.CommandContext(ctx, "devpod", "stop", stopParams.Name)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to stop workspace: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    stopParams.Name,
			"message": "Workspace stopped successfully",
			"output":  string(output),
		}, nil
	})

	// Delete workspace
	server.RegisterHandler("devpod_deleteWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var deleteParams struct {
			Name  string `json:"name"`
			Force bool   `json:"force,omitempty"`
		}

		if err := json.Unmarshal(params, &deleteParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid delete workspace parameters")
		}

		if deleteParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Workspace name is required")
		}

		args := []string{"delete", deleteParams.Name}
		if deleteParams.Force {
			args = append(args, "--force")
		}

		cmd := exec.CommandContext(ctx, "devpod", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to delete workspace: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    deleteParams.Name,
			"message": "Workspace deleted successfully",
			"output":  string(output),
		}, nil
	})

	// List providers
	server.RegisterHandler("devpod_listProviders", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		cmd := exec.CommandContext(ctx, "devpod", "provider", "list", "--output", "json")
		output, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("failed to list providers: %w", err)
		}

		var providers []DevPodProvider
		if err := json.Unmarshal(output, &providers); err != nil {
			// If JSON parsing fails, try to parse the text output
			return parseTextProviderList(string(output)), nil
		}

		return map[string]interface{}{
			"providers": providers,
		}, nil
	})

	// Add provider
	server.RegisterHandler("devpod_addProvider", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var addParams struct {
			Name    string            `json:"name"`
			Options map[string]string `json:"options,omitempty"`
		}

		if err := json.Unmarshal(params, &addParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid add provider parameters")
		}

		if addParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Provider name is required")
		}

		args := []string{"provider", "add", addParams.Name}
		for key, value := range addParams.Options {
			args = append(args, "-o", fmt.Sprintf("%s=%s", key, value))
		}

		cmd := exec.CommandContext(ctx, "devpod", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to add provider: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    addParams.Name,
			"message": "Provider added successfully",
			"output":  string(output),
		}, nil
	})

	// SSH into workspace
	server.RegisterHandler("devpod_ssh", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var sshParams struct {
			Name    string `json:"name"`
			Command string `json:"command,omitempty"`
		}

		if err := json.Unmarshal(params, &sshParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid SSH parameters")
		}

		if sshParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Workspace name is required")
		}

		args := []string{"ssh", sshParams.Name}
		if sshParams.Command != "" {
			args = append(args, "--command", sshParams.Command)
		}

		cmd := exec.CommandContext(ctx, "devpod", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return nil, fmt.Errorf("failed to SSH into workspace: %w\nOutput: %s", err, string(output))
		}

		return map[string]interface{}{
			"name":    sshParams.Name,
			"output":  string(output),
			"message": "SSH command executed successfully",
		}, nil
	})

	// Get workspace status
	server.RegisterHandler("devpod_status", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var statusParams struct {
			Name string `json:"name"`
		}

		if err := json.Unmarshal(params, &statusParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid status parameters")
		}

		if statusParams.Name == "" {
			return nil, mcp.NewInvalidParamsError("Workspace name is required")
		}

		cmd := exec.CommandContext(ctx, "devpod", "status", statusParams.Name, "--output", "json")
		output, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("failed to get workspace status: %w", err)
		}

		var status map[string]interface{}
		if err := json.Unmarshal(output, &status); err != nil {
			// If JSON parsing fails, return the text output
			return map[string]interface{}{
				"name":   statusParams.Name,
				"status": strings.TrimSpace(string(output)),
			}, nil
		}

		return status, nil
	})

	// Custom tools/call handler to route tool calls to our DevPod handlers
	server.RegisterHandler("tools/call", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		var callParams struct {
			Name      string                 `json:"name"`
			Arguments map[string]interface{} `json:"arguments"`
		}

		if err := json.Unmarshal(params, &callParams); err != nil {
			return nil, mcp.NewInvalidParamsError("Invalid tool call parameters")
		}

		// Handle framework's built-in echo tool
		if callParams.Name == "echo" {
			message, ok := callParams.Arguments["message"].(string)
			if !ok {
				return nil, mcp.NewInvalidParamsError("Missing or invalid 'message' parameter for echo tool")
			}
			return map[string]interface{}{
				"content": []map[string]interface{}{
					{
						"type": "text",
						"text": fmt.Sprintf("Echo: %s", message),
					},
				},
			}, nil
		}

		// Get the handler for DevPod tools
		handler := server.GetHandler(callParams.Name)
		if handler == nil {
			return nil, mcp.NewInvalidParamsError(fmt.Sprintf("Unknown tool: %s", callParams.Name))
		}

		// Convert arguments back to JSON for the handler
		argsBytes, err := json.Marshal(callParams.Arguments)
		if err != nil {
			return nil, mcp.NewInvalidParamsError("Failed to marshal tool arguments")
		}

		// Call the handler
		result, err := handler(ctx, argsBytes)
		if err != nil {
			return nil, err
		}

		// Wrap the result in the expected ToolsCallResult format
		return map[string]interface{}{
			"content": []map[string]interface{}{
				{
					"type": "text",
					"text": fmt.Sprintf("%v", result),
				},
			},
		}, nil
	})
}

// Helper function to parse text workspace list output
func parseTextWorkspaceList(output string) map[string]interface{} {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	workspaces := []map[string]string{}

	for _, line := range lines {
		if line == "" || strings.HasPrefix(line, "NAME") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) >= 3 {
			workspace := map[string]string{
				"name":     fields[0],
				"status":   fields[1],
				"provider": fields[2],
			}
			if len(fields) > 3 {
				workspace["ide"] = fields[3]
			}
			workspaces = append(workspaces, workspace)
		}
	}

	return map[string]interface{}{
		"workspaces": workspaces,
	}
}

// Helper function to parse text provider list output
func parseTextProviderList(output string) map[string]interface{} {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	providers := []map[string]string{}

	for _, line := range lines {
		if line == "" || strings.HasPrefix(line, "NAME") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) >= 2 {
			provider := map[string]string{
				"name":    fields[0],
				"version": fields[1],
			}
			if len(fields) > 2 && fields[2] == "*" {
				provider["default"] = "true"
			}
			providers = append(providers, provider)
		}
	}

	return map[string]interface{}{
		"providers": providers,
	}
}

// setupMessageHandler sets up the message handler for HTTP-based transports
func setupMessageHandler(server *mcp.Server, t mcp.Transport) {
	// Create a message handler function that processes JSON-RPC messages
	messageHandler := func(message []byte) ([]byte, error) {
		ctx := context.Background()

		var request mcp.JSONRPCRequest
		if err := json.Unmarshal(message, &request); err != nil {
			return nil, fmt.Errorf("invalid JSON-RPC message: %w", err)
		}

		// Check if this is a notification (no ID field)
		if request.ID == nil {
			// This is a notification - handle it and don't send a response
			if handler := server.GetNotificationHandler(request.Method); handler != nil {
				if err := handler(ctx, request.Params); err != nil {
					log.Printf("Error handling notification %s: %v", request.Method, err)
				}
			} else {
				log.Printf("No handler for notification: %s", request.Method)
			}
			// Return nil for notifications (no response expected)
			return nil, nil
		}

		// This is a request - handle it and send a response
		response := mcp.JSONRPCResponse{
			JSONRPC: mcp.JSONRPCVersion,
			ID:      request.ID,
		}

		// Get the handler for this method
		if handler := server.GetHandler(request.Method); handler != nil {
			result, err := handler(ctx, request.Params)
			if err != nil {
				if rpcErr, ok := err.(*mcp.RPCError); ok {
					response.Error = rpcErr
				} else {
					response.Error = &mcp.RPCError{
						Code:    mcp.InternalError,
						Message: err.Error(),
					}
				}
			} else {
				response.Result = result
			}
		} else {
			response.Error = &mcp.RPCError{
				Code:    mcp.MethodNotFound,
				Message: fmt.Sprintf("Method not found: %s", request.Method),
			}
		}

		// Marshal the response
		return json.Marshal(response)
	}

	// Set up message handler for SSE transport
	if sseTransport, ok := t.(*transport.SSETransport); ok {
		sseTransport.SetMessageHandler(messageHandler)
	}

	// Set up message handler for HTTP Streams transport
	if httpStreamsTransport, ok := t.(*transport.HTTPStreamsTransport); ok {
		httpStreamsTransport.SetMessageHandler(messageHandler)
	}
}
