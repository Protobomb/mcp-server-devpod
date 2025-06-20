#!/usr/bin/env python3
"""
HTTP Streams Integration Test Script for MCP DevPod Server
This script tests the HTTP Streams transport with proper SSE stream handling.
"""

import json
import requests
import time
import sys
import threading
import subprocess
import signal
import os
from urllib.parse import urljoin

class HTTPStreamsClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.mcp_url = f"{base_url}/mcp"
        self.sse_url = f"{base_url}/mcp"  # Same endpoint for SSE streams
        self.session_id = None
        self.session = requests.Session()
        self.responses = {}
        self.running = False
        self.sse_thread = None
        self.stop_event = threading.Event()
        
    def start_sse_stream(self):
        """Start the SSE stream for receiving responses"""
        if not self.session_id:
            print("❌ Cannot start SSE stream without session ID")
            return False
            
        try:
            self.sse_thread = threading.Thread(target=self._listen_sse)
            self.sse_thread.daemon = True
            self.sse_thread.start()
            time.sleep(0.5)  # Give stream time to establish
            return self.running
        except Exception as e:
            print(f"Error starting SSE stream: {e}")
            return False
    
    def _listen_sse(self):
        """Listen for SSE events"""
        try:
            headers = {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Mcp-Session-Id': self.session_id
            }
            
            response = self.session.get(self.sse_url, headers=headers, stream=True, timeout=None)
            
            if response.status_code == 200:
                self.running = True
                print(f"✓ SSE stream established for session {self.session_id}")
                
                for line in response.iter_lines(decode_unicode=True):
                    if self.stop_event.is_set():
                        break
                        
                    if line and line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() and not data.startswith(':'):
                            try:
                                message = json.loads(data)
                                if 'id' in message:
                                    self.responses[message['id']] = message
                                    print(f"← SSE Response: {json.dumps(message, indent=2)}")
                            except json.JSONDecodeError:
                                pass
            else:
                print(f"❌ SSE stream failed with status {response.status_code}")
                                
        except Exception as e:
            print(f"SSE stream error: {e}")
        finally:
            self.running = False
    
    def send_message(self, message, wait_for_response=True):
        """Send a message to the MCP server"""
        try:
            headers = {"Content-Type": "application/json"}
            
            # Add session ID header if we have one
            if self.session_id:
                headers["Mcp-Session-Id"] = self.session_id
            
            response = self.session.post(
                self.mcp_url,
                json=message,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            # Extract session ID from response headers if present
            if 'Mcp-Session-Id' in response.headers:
                self.session_id = response.headers['Mcp-Session-Id']
                print(f"📝 Session ID: {self.session_id}")
            
            # For initialize, return direct response
            if message.get('method') == 'initialize':
                return response.json()
            
            # For other messages, wait for response via SSE if requested
            if wait_for_response and 'id' in message:
                request_id = message['id']
                # Wait for response via SSE stream
                for _ in range(50):  # Wait up to 5 seconds
                    if request_id in self.responses:
                        return self.responses.pop(request_id)
                    time.sleep(0.1)
                print(f"❌ Timeout waiting for response with ID {request_id}")
                return None
            
            # Handle empty responses (for notifications)
            if response.status_code == 204 or not response.text.strip():
                return None
            
            return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def close(self):
        """Close the client connection"""
        self.stop_event.set()
        if self.sse_thread and self.sse_thread.is_alive():
            self.sse_thread.join(timeout=1)

def test_mcp_workflow(base_url=None):
    """Test complete MCP workflow via HTTP Streams"""
    if base_url is None:
        base_url = "http://localhost:8080"
    
    print(f"🧪 Starting HTTP Streams Integration Test for DevPod Server")
    print(f"📡 Base URL: {base_url}")
    print(f"🔗 MCP Endpoint: {base_url}/mcp")
    print(f"📡 SSE Endpoint: {base_url}/mcp (GET)")
    print()
    
    # Test health endpoint first
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        health_response.raise_for_status()
        health_data = health_response.json()
        print(f"✓ Health check: {health_data}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Create HTTP Streams client
    client = HTTPStreamsClient(base_url)
    
    try:
        # Test 1: Initialize
        print("\n🚀 Test 1: Initialize")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "http-streams-integration-test",
                    "version": "1.0.0"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(init_message, indent=2)}")
        response = client.send_message(init_message)
        
        if response and response.get('result'):
            print(f"← Received: {json.dumps(response, indent=2)}")
            print(f"✓ Initialize successful")
        else:
            print(f"❌ Initialize failed: {response}")
            return False
        
        # Test 2: Start SSE stream
        print("\n📡 Test 2: Start SSE stream")
        if not client.start_sse_stream():
            print("❌ Failed to start SSE stream")
            return False
        
        # Test 3: List tools
        print("\n📋 Test 3: List tools")
        tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print(f"→ Sending: {json.dumps(tools_message, indent=2)}")
        response = client.send_message(tools_message)
        
        if response and response.get('result', {}).get('tools'):
            tools = response['result']['tools']
            print(f"✓ Tools list successful: {[tool['name'] for tool in tools]}")
            
            # Verify DevPod echo tool is present
            echo_tool = next((tool for tool in tools if tool['name'] == 'echo'), None)
            if echo_tool:
                print("✓ DevPod echo tool found in tools list")
            else:
                print("❌ DevPod echo tool not found in tools list")
                return False
        else:
            print(f"❌ Tools list failed: {response}")
            return False
        
        # Test 4: Call DevPod echo tool
        print("\n📋 Test 4: Call DevPod echo tool")
        call_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "message": "HTTP Streams integration test message"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(call_message, indent=2)}")
        response = client.send_message(call_message)
        
        if response and response.get('result', {}).get('content'):
            content = response['result']['content']
            print(f"✓ Tool call successful: {content}")
            
            # Verify the DevPod echo response
            expected_echo = "Echo: HTTP Streams integration test message"
            actual_echo = content[0]['text'] if content and len(content) > 0 else ""
            
            if actual_echo == expected_echo:
                print(f"✓ DevPod echo response verified: '{actual_echo}'")
            else:
                print(f"❌ DevPod echo response mismatch. Expected: '{expected_echo}', Got: '{actual_echo}'")
                return False
        else:
            print(f"❌ Tool call failed: {response}")
            return False
        
        # Test 5: Test DevPod listWorkspaces tool
        print("\n📋 Test 5: Test DevPod listWorkspaces tool")
        list_workspaces_message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "devpod_listWorkspaces",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(list_workspaces_message, indent=2)}")
        response = client.send_message(list_workspaces_message)
        
        if response and response.get('result', {}).get('content'):
            print("✓ DevPod listWorkspaces tool call successful")
        else:
            print(f"❌ DevPod listWorkspaces failed: {response}")
            return False
        
        # Test 6: Test DevPod listProviders tool
        print("\n📋 Test 6: Test DevPod listProviders tool")
        list_providers_message = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "devpod_listProviders",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(list_providers_message, indent=2)}")
        response = client.send_message(list_providers_message)
        
        if response and response.get('result', {}).get('content'):
            print("✓ DevPod listProviders tool call successful")
        else:
            print(f"❌ DevPod listProviders failed: {response}")
            return False
        
        # Test 7: Test DevPod workspace status tool
        print("\n📋 Test 7: Test DevPod workspace status tool")
        status_message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "devpod_status",
                "arguments": {
                    "name": "test-workspace"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(status_message, indent=2)}")
        response = client.send_message(status_message)
        
        if response and response.get('error'):
            print(f"✓ DevPod status correctly failed for non-existent workspace: {response['error']['message']}")
        elif response and response.get('result', {}).get('content'):
            print("✓ DevPod status tool call successful")
        else:
            print(f"❌ DevPod status failed unexpectedly: {response}")
            return False
        
        # Test 8: Test DevPod createWorkspace validation
        print("\n📋 Test 8: Test DevPod createWorkspace validation")
        create_workspace_message = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "devpod_createWorkspace",
                "arguments": {
                    "name": "test-workspace-http",
                    "source": "https://github.com/example/repo"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(create_workspace_message, indent=2)}")
        response = client.send_message(create_workspace_message)
        
        if response and (response.get('result') or response.get('error')):
            print("✓ DevPod createWorkspace tool handled request (success or graceful error)")
        else:
            print(f"❌ DevPod createWorkspace failed unexpectedly: {response}")
            return False
        
        # Test 9: Test error handling with invalid tool
        print("\n📋 Test 9: Test error handling with invalid tool")
        invalid_call_message = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(invalid_call_message, indent=2)}")
        response = client.send_message(invalid_call_message)
        
        if response and response.get('error'):
            print("✓ Error handling works correctly for invalid tool")
        else:
            print(f"❌ Expected error response for invalid tool, got: {response}")
            return False
        
        # Test 10: Test DevPod tool with invalid arguments
        print("\n📋 Test 10: Test DevPod tool with invalid arguments")
        invalid_args_message = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "devpod_status",
                "arguments": {}  # Missing required 'name' argument
            }
        }
        
        print(f"→ Sending: {json.dumps(invalid_args_message, indent=2)}")
        response = client.send_message(invalid_args_message)
        
        if response and (response.get('error') or response.get('result')):
            print("✓ DevPod tool handled invalid arguments gracefully")
        else:
            print(f"❌ DevPod tool failed to handle invalid arguments: {response}")
            return False
        
        print("\n🎉 All HTTP Streams DevPod tests passed!")
        return True
            
    finally:
        client.close()

def start_server(port=8080):
    """Start the MCP server for testing"""
    try:
        # Build the server first
        print("🔨 Building DevPod MCP server...")
        build_result = subprocess.run(['go', 'build', '-o', 'mcp-server-devpod', 'main.go'], 
                                    capture_output=True, text=True, timeout=30)
        if build_result.returncode != 0:
            print(f"❌ Build failed: {build_result.stderr}")
            return None
        
        print("✓ Build successful")
        
        # Start the server
        print(f"🚀 Starting HTTP Streams server on port {port}...")
        server_process = subprocess.Popen([
            './mcp-server-devpod', 
            '-transport', 'http-streams', 
            '-addr', str(port)
        ])
        
        # Wait for server to start
        time.sleep(2)
        
        # Check if server is running
        try:
            health_response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if health_response.status_code == 200:
                print(f"✓ Server started successfully on port {port}")
                return server_process
            else:
                print(f"❌ Server health check failed")
                server_process.terminate()
                return None
        except Exception as e:
            print(f"❌ Server not responding: {e}")
            server_process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def main():
    """Main test function - runs HTTP Streams transport test with its own server"""
    import argparse
    parser = argparse.ArgumentParser(description="Test HTTP Streams transport for DevPod MCP Server")
    parser.add_argument("--port", type=int, default=8081, help="Port to run server on")
    parser.add_argument("--external-server", action="store_true", 
                       help="Use external server instead of starting our own")
    
    args = parser.parse_args()
    
    port = args.port
    base_url = f"http://localhost:{port}"
    server_process = None
    
    print("🧪 Starting HTTP Streams Transport Integration Test for DevPod MCP Server")
    print(f"📡 Testing on port {port}")
    
    try:
        if not args.external_server:
            # Start our own HTTP Streams server
            print(f"🚀 Starting HTTP Streams server on port {port} for integration test...")
            server_process = start_server(port)
            if not server_process:
                print("❌ Failed to start HTTP Streams server")
                sys.exit(1)
        else:
            # Check if external server is running
            try:
                health_response = requests.get(f"{base_url}/health", timeout=2)
                if health_response.status_code != 200:
                    print(f"❌ External server not responding at {base_url}")
                    sys.exit(1)
                print(f"✓ Using external server at {base_url}")
            except Exception as e:
                print(f"❌ External server not available: {e}")
                sys.exit(1)
        
        # Run the test
        success = test_mcp_workflow(base_url)
        
        if success:
            print("\n🎉 HTTP Streams integration test PASSED!")
            sys.exit(0)
        else:
            print("\n❌ HTTP Streams integration test FAILED!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
    finally:
        if server_process:
            print("\n🛑 Stopping HTTP Streams server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

if __name__ == "__main__":
    main()