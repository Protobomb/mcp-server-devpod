package main

import (
	"testing"
)

func TestToolDefinitions(t *testing.T) {
	tools := getTools()
	
	expectedTools := []string{
		"devpod.listWorkspaces",
		"devpod.createWorkspace",
		"devpod.startWorkspace",
		"devpod.stopWorkspace",
		"devpod.deleteWorkspace",
		"devpod.sshWorkspace",
		"devpod.getWorkspaceStatus",
		"devpod.listProviders",
		"devpod.addProvider",
	}
	
	if len(tools) != len(expectedTools) {
		t.Errorf("Expected %d tools, got %d", len(expectedTools), len(tools))
	}
	
	// Check that all expected tools are present
	toolMap := make(map[string]bool)
	for _, tool := range tools {
		toolMap[tool.Name] = true
	}
	
	for _, expectedTool := range expectedTools {
		if !toolMap[expectedTool] {
			t.Errorf("Expected tool %s not found", expectedTool)
		}
	}
}

func TestErrorHandling(t *testing.T) {
	tests := []struct {
		name     string
		function func(map[string]interface{}) (interface{}, error)
		args     map[string]interface{}
		wantErr  bool
	}{
		{
			name:     "createWorkspace without name",
			function: createWorkspace,
			args:     map[string]interface{}{"source": "https://github.com/example/repo.git"},
			wantErr:  true,
		},
		{
			name:     "createWorkspace without source",
			function: createWorkspace,
			args:     map[string]interface{}{"name": "test"},
			wantErr:  true,
		},
		{
			name:     "startWorkspace without name",
			function: startWorkspace,
			args:     map[string]interface{}{},
			wantErr:  true,
		},
		{
			name:     "stopWorkspace without name",
			function: stopWorkspace,
			args:     map[string]interface{}{},
			wantErr:  true,
		},
		{
			name:     "deleteWorkspace without name",
			function: deleteWorkspace,
			args:     map[string]interface{}{},
			wantErr:  true,
		},
		{
			name:     "sshWorkspace without name",
			function: sshWorkspace,
			args:     map[string]interface{}{},
			wantErr:  true,
		},
		{
			name:     "getWorkspaceStatus without name",
			function: getWorkspaceStatus,
			args:     map[string]interface{}{},
			wantErr:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := tt.function(tt.args)
			if (err != nil) != tt.wantErr {
				t.Errorf("%s() error = %v, wantErr %v", tt.name, err, tt.wantErr)
			}
		})
	}
}

func TestMainFlags(t *testing.T) {
	// Test that the main function accepts the expected flags
	// This is a simple test to ensure the flags are defined
	tests := []struct {
		flag     string
		expected string
	}{
		{"-transport", "stdio"},
		{"-addr", ":8080"},
	}
	
	// Since we can't easily test main() directly, we just verify
	// that the flag variables exist and have expected defaults
	if transport != "stdio" {
		t.Errorf("Expected default transport to be 'stdio', got '%s'", transport)
	}
	
	if addr != ":8080" {
		t.Errorf("Expected default addr to be ':8080', got '%s'", addr)
	}
}