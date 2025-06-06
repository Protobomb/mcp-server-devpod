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

	"github.com/openhands/mcp-server-framework/pkg/mcp"
	"github.com/openhands/mcp-server-framework/pkg/transport"
)

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
	var (
		transportType = flag.String("transport", "stdio", "Transport type: stdio or sse")
		addr          = flag.String("addr", ":8080", "Address for SSE transport")
	)
	flag.Parse()

	// Create transport
	var t mcp.Transport
	switch *transportType {
	case "stdio":
		t = transport.NewSTDIOTransport()
	case "sse":
		t = transport.NewSSETransport(*addr)
	default:
		log.Fatalf("Unknown transport type: %s", *transportType)
	}

	// Create server
	server := mcp.NewServer(t)

	// Register DevPod handlers
	registerDevPodHandlers(server)

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

	// Start server
	if err := server.Start(ctx); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}

	log.Printf("DevPod MCP server started with %s transport", *transportType)
	if *transportType == "sse" {
		log.Printf("Listening on %s", *addr)
	}

	// Wait for context cancellation
	<-ctx.Done()

	// Cleanup
	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}

	if err := server.Close(); err != nil {
		log.Printf("Error closing server: %v", err)
	}

	log.Println("Server stopped")
}

func registerDevPodHandlers(server *mcp.Server) {
	// List workspaces
	server.RegisterHandler("devpod.listWorkspaces", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.createWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.startWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.stopWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.deleteWorkspace", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.listProviders", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.addProvider", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
			args = append(args, fmt.Sprintf("--%s=%s", key, value))
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
	server.RegisterHandler("devpod.ssh", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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
	server.RegisterHandler("devpod.status", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
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

	// List available tools
	server.RegisterHandler("tools/list", func(ctx context.Context, params json.RawMessage) (interface{}, error) {
		tools := []map[string]interface{}{
			{
				"name":        "devpod.listWorkspaces",
				"description": "List all DevPod workspaces",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{},
				},
			},
			{
				"name":        "devpod.createWorkspace",
				"description": "Create a new DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
						},
						"source": map[string]interface{}{
							"type":        "string",
							"description": "Source repository or path",
						},
						"provider": map[string]interface{}{
							"type":        "string",
							"description": "Provider to use (optional)",
						},
						"ide": map[string]interface{}{
							"type":        "string",
							"description": "IDE to use (optional)",
						},
					},
					"required": []string{"name", "source"},
				},
			},
			{
				"name":        "devpod.startWorkspace",
				"description": "Start a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
						},
						"ide": map[string]interface{}{
							"type":        "string",
							"description": "IDE to use (optional)",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod.stopWorkspace",
				"description": "Stop a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod.deleteWorkspace",
				"description": "Delete a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
						},
						"force": map[string]interface{}{
							"type":        "boolean",
							"description": "Force delete without confirmation",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod.listProviders",
				"description": "List all DevPod providers",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{},
				},
			},
			{
				"name":        "devpod.addProvider",
				"description": "Add a new DevPod provider",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the provider",
						},
						"options": map[string]interface{}{
							"type":        "object",
							"description": "Provider-specific options",
						},
					},
					"required": []string{"name"},
				},
			},
			{
				"name":        "devpod.ssh",
				"description": "SSH into a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
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
				"name":        "devpod.status",
				"description": "Get status of a DevPod workspace",
				"inputSchema": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the workspace",
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
				"provider": fields[1],
				"status":   fields[2],
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