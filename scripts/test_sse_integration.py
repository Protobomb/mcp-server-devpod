#!/usr/bin/env python3
"""
SSE Integration Test Script for MCP DevPod Server
This script properly handles SSE connections and MCP protocol testing.
"""

import json
import requests
import threading
import time
import sys
import subprocess
import signal
import os
from urllib.parse import urljoin

class SSEClient:
    def __init__(self, base_url, session_id):
        self.base_url = base_url
        self.session_id = session_id
        self.sse_url = f"{base_url}/sse?sessionId={session_id}"
        self.message_url = f"{base_url}/message?sessionId={session_id}"
        self.responses = []
        self.connected = False
        self.stop_event = threading.Event()
        self.sse_thread = None
        
    def connect(self):
        """Connect to SSE endpoint and start listening for messages"""
        self.sse_thread = threading.Thread(target=self._listen_sse)
        self.sse_thread.daemon = True
        self.sse_thread.start()
        
        # Wait for connection
        for _ in range(50):  # 5 seconds timeout
            if self.connected:
                return True
            time.sleep(0.1)
        return False
    
    def _listen_sse(self):
        """Listen to SSE stream"""
        try:
            response = requests.get(
                self.sse_url,
                headers={'Accept': 'text/event-stream'},
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            current_event = None
            for line in response.iter_lines(decode_unicode=True):
                if self.stop_event.is_set():
                    break
                
                if line.startswith('event: '):
                    current_event = line[7:]  # Remove 'event: ' prefix
                elif line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    
                    if current_event == 'endpoint':
                        # This is the endpoint URL for posting messages
                        self.connected = True
                        print(f"✓ SSE connected, endpoint: {data}")
                    elif current_event == 'message':
                        # This is an MCP message
                        try:
                            message = json.loads(data)
                            self.responses.append(message)
                            print(f"← Received: {json.dumps(message, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"Invalid JSON in message data: {data}")
                    else:
                        # Try to parse as JSON for backward compatibility
                        try:
                            message = json.loads(data)
                            if message.get('type') == 'connected':
                                self.connected = True
                                print(f"✓ SSE connected with session: {message.get('sessionId')}")
                            else:
                                self.responses.append(message)
                                print(f"← Received: {json.dumps(message, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"Unknown event '{current_event}' with data: {data}")
                elif line == '':
                    # Empty line resets the event type
                    current_event = None
                        
        except Exception as e:
            print(f"SSE connection error: {e}")
    
    def send_message(self, message):
        """Send a message via POST and return the HTTP response"""
        try:
            response = requests.post(
                self.message_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            # For HTTP 202 Accepted, we expect plain text response
            if response.status_code == 202:
                return {"status": "accepted", "text": response.text}
            else:
                return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def wait_for_response(self, request_id=None, timeout=5):
        """Wait for a response from SSE stream"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Look for response with matching ID
            for i, response in enumerate(self.responses):
                if request_id is None or response.get('id') == request_id:
                    # Remove the response from the list to avoid reusing it
                    return self.responses.pop(i)
            time.sleep(0.1)
        return None
    
    def disconnect(self):
        """Disconnect from SSE"""
        self.stop_event.set()
        if self.sse_thread:
            self.sse_thread.join(timeout=2)

def test_mcp_workflow(base_url=None):
    """Test complete MCP workflow"""
    if base_url is None:
        base_url = "http://localhost:8080"
    session_id = f"test-session-{int(time.time())}"
    
    print(f"🧪 Starting MCP Integration Test for DevPod Server")
    print(f"📡 Base URL: {base_url}")
    print(f"🆔 Session ID: {session_id}")
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
    
    # Create SSE client
    client = SSEClient(base_url, session_id)
    
    try:
        # Connect to SSE
        print("🔌 Connecting to SSE...")
        if not client.connect():
            print("❌ Failed to connect to SSE")
            return False
        
        # Test 1: Initialize
        print("\n📋 Test 1: Initialize")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "sse-integration-test",
                    "version": "1.0.0"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(init_message, indent=2)}")
        post_response = client.send_message(init_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for MCP response via SSE
        mcp_response = client.wait_for_response(request_id=1, timeout=5)
        if mcp_response and mcp_response.get('result', {}).get('protocolVersion'):
            print("✓ Initialize successful")
        else:
            print(f"❌ Initialize failed: {mcp_response}")
            return False
        
        # Test 2: Initialized notification
        print("\n📋 Test 2: Initialized notification")
        initialized_message = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
        
        print(f"→ Sending: {json.dumps(initialized_message, indent=2)}")
        post_response = client.send_message(initialized_message)
        print(f"📤 POST response: {post_response}")
        
        # For notifications, we don't expect a response, just check if POST was successful
        if post_response and post_response.get('status') == 'accepted':
            print("✓ Initialized notification sent successfully")
        else:
            print(f"❌ Initialized notification failed: {post_response}")
        
        # Small delay to let any responses arrive
        time.sleep(0.5)
        
        # Test 3: List tools
        print("\n📋 Test 3: List tools")
        tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print(f"→ Sending: {json.dumps(tools_message, indent=2)}")
        post_response = client.send_message(tools_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for MCP response via SSE
        mcp_response = client.wait_for_response(request_id=2, timeout=5)
        if mcp_response and mcp_response.get('result', {}).get('tools'):
            tools = mcp_response['result']['tools']
            print(f"✓ Tools list successful: {[tool['name'] for tool in tools]}")
            
            # Verify DevPod echo tool is present
            echo_tool = next((tool for tool in tools if tool['name'] == 'echo'), None)
            if echo_tool:
                print("✓ DevPod echo tool found in tools list")
            else:
                print("❌ DevPod echo tool not found in tools list")
                return False
        else:
            print(f"❌ Tools list failed: {mcp_response}")
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
                    "message": "SSE integration test message"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(call_message, indent=2)}")
        post_response = client.send_message(call_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for MCP response via SSE
        mcp_response = client.wait_for_response(request_id=3, timeout=5)
        if mcp_response and mcp_response.get('result', {}).get('content'):
            content = mcp_response['result']['content']
            print(f"✓ Tool call successful: {content}")
            
            # Verify the DevPod echo response
            expected_echo = "Echo: SSE integration test message"
            actual_echo = content[0]['text'] if content and len(content) > 0 else ""
            if actual_echo == expected_echo:
                print("✓ DevPod echo response matches expected output")
            else:
                print(f"❌ DevPod echo mismatch. Expected: '{expected_echo}', Got: '{actual_echo}'")
                return False
        else:
            print(f"❌ Tool call failed: {mcp_response}")
            return False
        
        # Test 5: Test error handling with invalid tool
        print("\n📋 Test 5: Test error handling with invalid tool")
        invalid_call_message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(invalid_call_message, indent=2)}")
        post_response = client.send_message(invalid_call_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for MCP response via SSE
        mcp_response = client.wait_for_response(request_id=4, timeout=5)
        if mcp_response and mcp_response.get('error'):
            print("✓ Error handling works correctly for invalid tool")
        else:
            print(f"❌ Expected error response for invalid tool, got: {mcp_response}")
            return False
        
        print("\n🎉 All SSE DevPod tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        client.disconnect()

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
        print(f"🚀 Starting SSE server on port {port}...")
        server_process = subprocess.Popen([
            './mcp-server-devpod', 
            '-transport', 'sse', 
            '-addr', str(port)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(2)
        
        # Check if process is still alive
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server process exited with code {server_process.returncode}")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
        
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
    """Main test function - runs SSE transport test with its own server"""
    import argparse
    parser = argparse.ArgumentParser(description="Test SSE transport for DevPod MCP Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run server on")
    parser.add_argument("--external-server", action="store_true", 
                       help="Use external server instead of starting our own")
    
    args = parser.parse_args()
    
    port = args.port
    base_url = f"http://localhost:{port}"
    server_process = None
    
    print("🧪 Starting SSE Transport Integration Test for DevPod MCP Server")
    print(f"📡 Testing on port {port}")
    
    try:
        if not args.external_server:
            # Start our own SSE server
            print(f"🚀 Starting SSE server on port {port} for integration test...")
            server_process = start_server(port)
            if not server_process:
                print("❌ Failed to start SSE server")
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
            print("\n🎉 SSE integration test PASSED!")
            sys.exit(0)
        else:
            print("\n❌ SSE integration test FAILED!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
    finally:
        if server_process:
            print("\n🛑 Stopping SSE server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

if __name__ == "__main__":
    main()