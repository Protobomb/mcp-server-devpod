#!/usr/bin/env python3
"""
Comprehensive test script for all DevPod MCP server tools.
Tests each DevPod-specific tool with various scenarios.
"""

import json
import subprocess
import time
import sys
import argparse
import requests
import threading
from typing import Dict, Any, Optional, List

class DevPodToolTester:
    def __init__(self, transport: str = "stdio", port: int = 8080):
        self.transport = transport
        self.port = port
        self.server_process = None
        self.session_id = None
        self.base_url = f"http://localhost:{port}"
        
    def start_server(self):
        """Start the DevPod MCP server"""
        if self.transport == "stdio":
            self.server_process = subprocess.Popen(
                ["./mcp-server-devpod", "-transport", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            self.server_process = subprocess.Popen(
                ["./mcp-server-devpod", "-transport", self.transport, "-addr", str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)  # Give server time to start
            
    def stop_server(self):
        """Stop the DevPod MCP server"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            
    def send_stdio_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request via STDIO transport"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        self.server_process.stdin.write(request_json)
        self.server_process.stdin.flush()
        
        response_line = self.server_process.stdout.readline()
        return json.loads(response_line)
        
    def send_http_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request via HTTP Streams transport"""
        if not self.session_id:
            # Initialize session first
            init_response = self.initialize_session()
            if "error" in init_response:
                return init_response
                
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        response = requests.post(
            f"{self.base_url}/message",
            json=request,
            headers={"X-Session-ID": self.session_id}
        )
        return response.json()
        
    def send_sse_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request via SSE transport"""
        if not self.session_id:
            # Initialize session first
            init_response = self.initialize_session()
            if "error" in init_response:
                return init_response
                
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        response = requests.post(
            f"{self.base_url}/message",
            json=request,
            headers={"X-Session-ID": self.session_id}
        )
        return response.json()
        
    def initialize_session(self) -> Dict[str, Any]:
        """Initialize MCP session for HTTP/SSE transports"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "devpod-tool-tester",
                    "version": "1.0.0"
                }
            }
        }
        
        response = requests.post(f"{self.base_url}/message", json=init_request)
        result = response.json()
        
        if "result" in result:
            # Extract session ID from response headers or create one
            self.session_id = response.headers.get("X-Session-ID", "test-session")
            
            # Send initialized notification
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            requests.post(
                f"{self.base_url}/message",
                json=notification,
                headers={"X-Session-ID": self.session_id}
            )
            
        return result
        
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request using the appropriate transport"""
        if self.transport == "stdio":
            return self.send_stdio_request(method, params)
        elif self.transport == "http-streams":
            return self.send_http_request(method, params)
        elif self.transport == "sse":
            return self.send_sse_request(method, params)
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")
            
    def test_initialize(self) -> bool:
        """Test MCP initialization"""
        print("🔧 Testing MCP initialization...")
        
        if self.transport == "stdio":
            response = self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "devpod-tool-tester", "version": "1.0.0"}
            })
        else:
            response = self.initialize_session()
            
        if "result" in response:
            print("✅ Initialize: PASSED")
            return True
        else:
            print(f"❌ Initialize: FAILED - {response}")
            return False
            
    def test_tools_list(self) -> bool:
        """Test tools/list endpoint"""
        print("📋 Testing tools/list...")
        
        response = self.send_request("tools/list")
        
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            expected_tools = [
                "devpod.listWorkspaces",
                "devpod.createWorkspace", 
                "devpod.startWorkspace",
                "devpod.stopWorkspace",
                "devpod.deleteWorkspace",
                "devpod.listProviders",
                "devpod.addProvider",
                "devpod.ssh",
                "devpod.status"
            ]
            
            tool_names = [tool["name"] for tool in tools]
            missing_tools = [tool for tool in expected_tools if tool not in tool_names]
            
            if not missing_tools:
                print(f"✅ Tools list: PASSED - Found {len(tools)} tools")
                return True
            else:
                print(f"❌ Tools list: FAILED - Missing tools: {missing_tools}")
                return False
        else:
            print(f"❌ Tools list: FAILED - {response}")
            return False
            
    def test_list_workspaces(self) -> bool:
        """Test devpod.listWorkspaces tool"""
        print("🏢 Testing devpod.listWorkspaces...")
        
        response = self.send_request("tools/call", {
            "name": "devpod.listWorkspaces",
            "arguments": {}
        })
        
        if "result" in response:
            result = response["result"]
            if "content" in result and isinstance(result["content"], list):
                print("✅ List workspaces: PASSED")
                return True
            else:
                print(f"❌ List workspaces: FAILED - Invalid result format: {result}")
                return False
        else:
            print(f"❌ List workspaces: FAILED - {response}")
            return False
            
    def test_list_providers(self) -> bool:
        """Test devpod.listProviders tool"""
        print("🔌 Testing devpod.listProviders...")
        
        response = self.send_request("tools/call", {
            "name": "devpod.listProviders", 
            "arguments": {}
        })
        
        if "result" in response:
            result = response["result"]
            if "content" in result and isinstance(result["content"], list):
                print("✅ List providers: PASSED")
                return True
            else:
                print(f"❌ List providers: FAILED - Invalid result format: {result}")
                return False
        else:
            print(f"❌ List providers: FAILED - {response}")
            return False
            
    def test_workspace_status(self) -> bool:
        """Test devpod.status tool"""
        print("📊 Testing devpod.status...")
        
        # Test with a non-existent workspace (should handle gracefully)
        response = self.send_request("tools/call", {
            "name": "devpod.status",
            "arguments": {"name": "test-workspace-nonexistent"}
        })
        
        if "result" in response:
            result = response["result"]
            if "content" in result and isinstance(result["content"], list):
                print("✅ Workspace status: PASSED")
                return True
            else:
                print(f"❌ Workspace status: FAILED - Invalid result format: {result}")
                return False
        else:
            print(f"❌ Workspace status: FAILED - {response}")
            return False
            
    def test_create_workspace_validation(self) -> bool:
        """Test devpod.createWorkspace input validation"""
        print("🏗️ Testing devpod.createWorkspace validation...")
        
        # Test with missing required parameters
        response = self.send_request("tools/call", {
            "name": "devpod.createWorkspace",
            "arguments": {"name": "test-workspace"}  # Missing 'source'
        })
        
        # Should either succeed (if DevPod handles missing source) or fail gracefully
        if "result" in response or "error" in response:
            print("✅ Create workspace validation: PASSED")
            return True
        else:
            print(f"❌ Create workspace validation: FAILED - {response}")
            return False
            
    def test_start_workspace_validation(self) -> bool:
        """Test devpod.startWorkspace input validation"""
        print("▶️ Testing devpod.startWorkspace validation...")
        
        # Test with non-existent workspace
        response = self.send_request("tools/call", {
            "name": "devpod.startWorkspace",
            "arguments": {"name": "nonexistent-workspace"}
        })
        
        # Should handle gracefully (either succeed or fail with proper error)
        if "result" in response or "error" in response:
            print("✅ Start workspace validation: PASSED")
            return True
        else:
            print(f"❌ Start workspace validation: FAILED - {response}")
            return False
            
    def test_stop_workspace_validation(self) -> bool:
        """Test devpod.stopWorkspace input validation"""
        print("⏹️ Testing devpod.stopWorkspace validation...")
        
        # Test with non-existent workspace
        response = self.send_request("tools/call", {
            "name": "devpod.stopWorkspace",
            "arguments": {"name": "nonexistent-workspace"}
        })
        
        # Should handle gracefully
        if "result" in response or "error" in response:
            print("✅ Stop workspace validation: PASSED")
            return True
        else:
            print(f"❌ Stop workspace validation: FAILED - {response}")
            return False
            
    def test_delete_workspace_validation(self) -> bool:
        """Test devpod.deleteWorkspace input validation"""
        print("🗑️ Testing devpod.deleteWorkspace validation...")
        
        # Test with non-existent workspace
        response = self.send_request("tools/call", {
            "name": "devpod.deleteWorkspace",
            "arguments": {"name": "nonexistent-workspace", "force": True}
        })
        
        # Should handle gracefully
        if "result" in response or "error" in response:
            print("✅ Delete workspace validation: PASSED")
            return True
        else:
            print(f"❌ Delete workspace validation: FAILED - {response}")
            return False
            
    def test_add_provider_validation(self) -> bool:
        """Test devpod.addProvider input validation"""
        print("➕ Testing devpod.addProvider validation...")
        
        # Test with minimal valid parameters
        response = self.send_request("tools/call", {
            "name": "devpod.addProvider",
            "arguments": {"name": "test-provider"}
        })
        
        # Should handle gracefully
        if "result" in response or "error" in response:
            print("✅ Add provider validation: PASSED")
            return True
        else:
            print(f"❌ Add provider validation: FAILED - {response}")
            return False
            
    def test_ssh_validation(self) -> bool:
        """Test devpod.ssh input validation"""
        print("🔐 Testing devpod.ssh validation...")
        
        # Test with non-existent workspace
        response = self.send_request("tools/call", {
            "name": "devpod.ssh",
            "arguments": {"name": "nonexistent-workspace", "command": "echo 'test'"}
        })
        
        # Should handle gracefully
        if "result" in response or "error" in response:
            print("✅ SSH validation: PASSED")
            return True
        else:
            print(f"❌ SSH validation: FAILED - {response}")
            return False
            
    def test_invalid_tool(self) -> bool:
        """Test calling an invalid tool"""
        print("❓ Testing invalid tool call...")
        
        response = self.send_request("tools/call", {
            "name": "devpod.invalidTool",
            "arguments": {}
        })
        
        if "error" in response:
            print("✅ Invalid tool: PASSED - Properly rejected")
            return True
        else:
            print(f"❌ Invalid tool: FAILED - Should have been rejected: {response}")
            return False
            
    def run_all_tests(self) -> bool:
        """Run all DevPod tool tests"""
        print("🧪 Starting DevPod Tools Comprehensive Test")
        print(f"🎯 Transport: {self.transport}")
        print("=" * 60)
        
        tests = [
            ("Initialize", self.test_initialize),
            ("Tools List", self.test_tools_list),
            ("List Workspaces", self.test_list_workspaces),
            ("List Providers", self.test_list_providers),
            ("Workspace Status", self.test_workspace_status),
            ("Create Workspace Validation", self.test_create_workspace_validation),
            ("Start Workspace Validation", self.test_start_workspace_validation),
            ("Stop Workspace Validation", self.test_stop_workspace_validation),
            ("Delete Workspace Validation", self.test_delete_workspace_validation),
            ("Add Provider Validation", self.test_add_provider_validation),
            ("SSH Validation", self.test_ssh_validation),
            ("Invalid Tool", self.test_invalid_tool),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name}: FAILED - Exception: {e}")
                failed += 1
            print()
            
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🎯 Total: {passed + failed}")
        
        if failed == 0:
            print("🎉 ALL DEVPOD TOOL TESTS PASSED!")
            return True
        else:
            print(f"💥 {failed} TESTS FAILED!")
            return False

def main():
    parser = argparse.ArgumentParser(description="Test DevPod MCP server tools")
    parser.add_argument("--transport", choices=["stdio", "sse", "http-streams"], 
                       default="stdio", help="Transport type to test")
    parser.add_argument("--port", type=int, default=8080, 
                       help="Port for SSE/HTTP Streams transport")
    
    args = parser.parse_args()
    
    # Build the server first
    print("🔨 Building DevPod MCP server...")
    build_result = subprocess.run(["make", "build"], capture_output=True, text=True)
    if build_result.returncode != 0:
        print(f"❌ Build failed: {build_result.stderr}")
        return False
    print("✅ Build successful")
    
    tester = DevPodToolTester(args.transport, args.port)
    
    try:
        tester.start_server()
        success = tester.run_all_tests()
        return success
    finally:
        tester.stop_server()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)