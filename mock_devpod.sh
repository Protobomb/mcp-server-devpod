#!/bin/bash
# Mock DevPod script for testing the MCP server

case "$1" in
    "list")
        if [ "$2" == "--output" ] && [ "$3" == "json" ]; then
            echo '[
                {
                    "id": "test-workspace",
                    "uid": "test-workspace",
                    "source": {
                        "gitRepository": "https://github.com/example/test-repo.git"
                    },
                    "machine": {
                        "id": "test-workspace.devpod",
                        "folder": "/home/user/.devpod/contexts/default/workspaces/test-workspace",
                        "provider": {
                            "name": "docker"
                        },
                        "state": {
                            "state": "Running"
                        },
                        "creationTimestamp": "2024-01-01T00:00:00Z"
                    },
                    "status": {
                        "phase": "Running"
                    }
                }
            ]'
        else
            echo "NAME            PROVIDER    STATUS"
            echo "test-workspace  docker      Running"
        fi
        ;;
    "provider")
        if [ "$2" == "list" ] && [ "$3" == "--output" ] && [ "$4" == "json" ]; then
            echo '[
                {
                    "name": "docker",
                    "displayName": "Docker",
                    "description": "Run workspaces in Docker containers",
                    "state": {
                        "initialized": true
                    },
                    "default": true
                },
                {
                    "name": "kubernetes",
                    "displayName": "Kubernetes",
                    "description": "Run workspaces in Kubernetes pods",
                    "state": {
                        "initialized": false
                    }
                }
            ]'
        else
            echo "NAME         USED"
            echo "docker       true"
            echo "kubernetes   false"
        fi
        ;;
    "status")
        if [ "$2" == "--output" ] && [ "$3" == "json" ]; then
            echo '{
                "id": "test-workspace",
                "context": "default",
                "provider": "docker",
                "state": "Running",
                "source": "https://github.com/example/test-repo.git"
            }'
        else
            echo "Status: Running"
        fi
        ;;
    "up")
        echo "Starting workspace $2..."
        echo "Workspace started successfully"
        ;;
    "stop")
        echo "Stopping workspace $2..."
        echo "Workspace stopped successfully"
        ;;
    "delete")
        echo "Deleting workspace $2..."
        echo "Workspace deleted successfully"
        ;;
    "ssh")
        if [ -n "$4" ]; then
            # Execute command
            echo "Executing command in workspace $2: ${@:4}"
            echo "Command output: Hello from mock DevPod!"
        else
            echo "SSH session to workspace $2"
            echo "Exit"
        fi
        ;;
    *)
        echo "DevPod Mock v0.1.0"
        echo "Usage: devpod [command]"
        echo ""
        echo "Commands:"
        echo "  list        List workspaces"
        echo "  up          Start a workspace"
        echo "  stop        Stop a workspace"
        echo "  delete      Delete a workspace"
        echo "  ssh         SSH into a workspace"
        echo "  provider    Manage providers"
        echo "  status      Show workspace status"
        ;;
esac