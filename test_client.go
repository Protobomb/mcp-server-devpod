//go:build ignore
// +build ignore

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"

	"github.com/protobomb/mcp-server-framework/pkg/client"
	"github.com/protobomb/mcp-server-framework/pkg/mcp"
)

func main() {
	// Create STDIO transport to connect to our server
	serverPath := "./mcp-server-devpod"
	if len(os.Args) > 1 {
		serverPath = os.Args[1]
	}

	// Check if server exists
	if _, err := os.Stat(serverPath); os.IsNotExist(err) {
		log.Fatalf("Server not found at %s. Please build it first with 'make build'", serverPath)
	}

	// Start the server process
	cmd := exec.Command(serverPath)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		log.Fatalf("Failed to create stdin pipe: %v", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		log.Fatalf("Failed to create stdout pipe: %v", err)
	}

	if err := cmd.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer func() {
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
	}()

	// Create client with STDIO transport
	t := client.NewSTDIOTransport(stdout, stdin)
	c := client.NewClient(t)
	defer c.Close()

	ctx := context.Background()

	// Start the client
	if err := c.Start(ctx); err != nil {
		log.Fatalf("Failed to start client: %v", err)
	}

	// Initialize connection
	clientInfo := mcp.ServerInfo{
		Name:    "test-client",
		Version: "1.0.0",
	}

	fmt.Println("Initializing connection...")
	result, err := c.Initialize(ctx, clientInfo)
	if err != nil {
		log.Fatalf("Failed to initialize: %v", err)
	}
	fmt.Printf("Connected to server: %s v%s\n", result.ServerInfo.Name, result.ServerInfo.Version)

	// List available tools
	fmt.Println("\nListing available tools...")
	tools, err := c.ListTools(ctx)
	if err != nil {
		log.Printf("Failed to list tools: %v", err)
	} else {
		toolsJSON, _ := json.MarshalIndent(tools, "", "  ")
		fmt.Printf("Available tools:\n%s\n", toolsJSON)
	}

	// Try to list workspaces
	fmt.Println("\nListing DevPod workspaces...")
	workspacesResult, err := c.CallTool(ctx, "devpod.listWorkspaces", nil)
	if err != nil {
		log.Printf("Failed to list workspaces: %v", err)
	} else {
		workspacesJSON, _ := json.MarshalIndent(workspacesResult, "", "  ")
		fmt.Printf("Workspaces:\n%s\n", workspacesJSON)
	}

	// Try to list providers
	fmt.Println("\nListing DevPod providers...")
	providersResult, err := c.CallTool(ctx, "devpod.listProviders", nil)
	if err != nil {
		log.Printf("Failed to list providers: %v", err)
	} else {
		providersJSON, _ := json.MarshalIndent(providersResult, "", "  ")
		fmt.Printf("Providers:\n%s\n", providersJSON)
	}

	fmt.Println("\nTest completed successfully!")
}