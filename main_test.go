package main

import (
	"testing"
)

func TestParseTextWorkspaceList(t *testing.T) {
	// Test the parseTextWorkspaceList function
	testOutput := `NAME    STATUS    PROVIDER
test1   Running   docker
test2   Stopped   kubernetes`

	result := parseTextWorkspaceList(testOutput)
	workspaces, ok := result["workspaces"].([]map[string]string)
	if !ok {
		t.Fatal("Expected workspaces to be []map[string]string")
	}

	if len(workspaces) != 2 {
		t.Errorf("Expected 2 workspaces, got %d", len(workspaces))
	}

	if workspaces[0]["name"] != "test1" || workspaces[0]["status"] != "Running" {
		t.Errorf("Unexpected workspace data: %v", workspaces[0])
	}
}

func TestParseTextProviderList(t *testing.T) {
	// Test the parseTextProviderList function
	testOutput := `NAME         VERSION
docker       v0.1.0
kubernetes   v0.2.0`

	result := parseTextProviderList(testOutput)
	providers, ok := result["providers"].([]map[string]string)
	if !ok {
		t.Fatal("Expected providers to be []map[string]string")
	}

	if len(providers) != 2 {
		t.Errorf("Expected 2 providers, got %d", len(providers))
	}

	if providers[0]["name"] != "docker" || providers[0]["version"] != "v0.1.0" {
		t.Errorf("Unexpected provider data: %v", providers[0])
	}
}