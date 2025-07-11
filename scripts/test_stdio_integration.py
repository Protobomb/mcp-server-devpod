#!/usr/bin/env python3
"""
STDIO Integration Test Script for MCP DevPod Server
This script tests the STDIO transport by launching the server process and communicating via stdin/stdout.
"""

import json
import subprocess
import threading
import time
import sys
import queue
import os

class STDIOClient:
    def __init__(self, command):
        self.command = command
        self.process = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.stdout_thread = None
        self.stderr_thread = None
        
    def start(self):
        """Start the STDIO server process"""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Start threads to read stdout and stderr
            self.stdout_thread = threading.Thread(target=self._read_stdout)
            self.stderr_thread = threading.Thread(target=self._read_stderr)
            self.stdout_thread.daemon = True
            self.stderr_thread.daemon = True
            self.stdout_thread.start()
            self.stderr_thread.start()
            
            return True
        except Exception as e:
            print(f"Failed to start process: {e}")
            return False
    
    def _read_stdout(self):
        """Read stdout in a separate thread"""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line.strip():
                    self.stdout_queue.put(line.strip())
        except Exception as e:
            print(f"Error reading stdout: {e}")
    
    def _read_stderr(self):
        """Read stderr in a separate thread"""
        try:
            for line in iter(self.process.stderr.readline, ''):
                if line.strip():
                    self.stderr_queue.put(line.strip())
        except Exception as e:
            print(f"Error reading stderr: {e}")
    
    def send_message(self, message):
        """Send a JSON-RPC message to the server"""
        try:
            json_str = json.dumps(message)
            print(f"→ Sending: {json_str}")
            self.process.stdin.write(json_str + '\n')
            self.process.stdin.flush()
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def wait_for_response(self, timeout=5):
        """Wait for a response from the server"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check for stdout (JSON responses)
                response_line = self.stdout_queue.get(timeout=0.1)
                try:
                    response = json.loads(response_line)
                    print(f"← Received: {json.dumps(response, indent=2)}")
                    return response
                except json.JSONDecodeError:
                    print(f"Non-JSON stdout: {response_line}")
                    continue
            except queue.Empty:
                # Check for stderr (debug/error messages)
                try:
                    stderr_line = self.stderr_queue.get_nowait()
                    print(f"🔍 Server log: {stderr_line}")
                except queue.Empty:
                    pass
                continue
        
        print(f"⏰ Timeout waiting for response")
        return None
    
    def stop(self):
        """Stop the server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

def test_mcp_workflow(server_binary=None):
    """Test complete MCP workflow via STDIO"""
    if server_binary is None:
        server_binary = "./mcp-server-devpod"
    
    # Check if binary exists
    if not os.path.exists(server_binary):
        print(f"❌ Server binary not found: {server_binary}")
        return False
    
    command = [server_binary, "-transport", "stdio"]
    
    print(f"🧪 Starting STDIO Integration Test for DevPod MCP Server")
    print(f"📡 Command: {' '.join(command)}")
    print()
    
    # Create STDIO client
    client = STDIOClient(command)
    
    try:
        # Start the server process
        print("🚀 Starting STDIO server...")
        if not client.start():
            print("❌ Failed to start STDIO server")
            return False
        
        # Give the server a moment to start
        time.sleep(0.5)
        
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
                    "name": "stdio-integration-test",
                    "version": "1.0.0"
                }
            }
        }
        
        if not client.send_message(init_message):
            print("❌ Failed to send initialize message")
            return False
        
        response = client.wait_for_response(timeout=5)
        if response and response.get('result', {}).get('protocolVersion'):
            print("✓ Initialize successful")
        else:
            print(f"❌ Initialize failed: {response}")
            return False
        
        # Test 2: Initialized notification
        print("\n📋 Test 2: Initialized notification")
        initialized_message = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        if not client.send_message(initialized_message):
            print("❌ Failed to send initialized notification")
            return False
        
        # For notifications, we don't expect a JSON response, just check logs
        time.sleep(0.5)
        print("✓ Initialized notification sent successfully")
        
        # Test 3: List tools
        print("\n📋 Test 3: List tools")
        tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        if not client.send_message(tools_message):
            print("❌ Failed to send tools/list message")
            return False
        
        response = client.wait_for_response(timeout=5)
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
                    "message": "STDIO integration test message"
                }
            }
        }
        
        if not client.send_message(call_message):
            print("❌ Failed to send tools/call message")
            return False
        
        response = client.wait_for_response(timeout=5)
        if response and response.get('result', {}).get('content'):
            content = response['result']['content']
            print(f"✓ Tool call successful: {content}")
            
            # Verify the DevPod echo response
            expected_echo = "Echo: STDIO integration test message"
            actual_echo = content[0]['text'] if content and len(content) > 0 else ""
            if actual_echo == expected_echo:
                print("✓ DevPod echo response matches expected output")
            else:
                print(f"❌ DevPod echo mismatch. Expected: '{expected_echo}', Got: '{actual_echo}'")
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
        
        if not client.send_message(list_workspaces_message):
            print("❌ Failed to send devpod_listWorkspaces message")
            return False
        
        response = client.wait_for_response(timeout=10)
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
        
        if not client.send_message(list_providers_message):
            print("❌ Failed to send devpod_listProviders message")
            return False
        
        response = client.wait_for_response(timeout=10)
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
        
        if not client.send_message(status_message):
            print("❌ Failed to send devpod_status message")
            return False
        
        response = client.wait_for_response(timeout=10)
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
                    "name": "test-workspace-validation",
                    "source": "https://github.com/example/repo"
                }
            }
        }
        
        if not client.send_message(create_workspace_message):
            print("❌ Failed to send devpod_createWorkspace message")
            return False
        
        response = client.wait_for_response(timeout=15)
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
        
        if not client.send_message(invalid_call_message):
            print("❌ Failed to send invalid tools/call message")
            return False
        
        response = client.wait_for_response(timeout=5)
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
        
        if not client.send_message(invalid_args_message):
            print("❌ Failed to send invalid arguments message")
            return False
        
        response = client.wait_for_response(timeout=5)
        if response and (response.get('error') or response.get('result')):
            print("✓ DevPod tool handled invalid arguments gracefully")
        else:
            print(f"❌ DevPod tool failed to handle invalid arguments: {response}")
            return False
        
        print("\n🎉 All STDIO DevPod tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        client.stop()

def main():
    """Main test function - runs STDIO transport test"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test STDIO transport for DevPod MCP Server")
    parser.add_argument("--server-binary", default="./mcp-server-devpod", 
                       help="Path to the server binary")
    
    args = parser.parse_args()
    
    print("🧪 Starting STDIO Transport Integration Test for DevPod MCP Server")
    print(f"📡 Testing with binary: {args.server_binary}")
    
    # Build the server first if it doesn't exist
    if not os.path.exists(args.server_binary):
        print("🔨 Building DevPod MCP server...")
        try:
            build_result = subprocess.run(['go', 'build', '-o', args.server_binary, 'main.go'], 
                                        capture_output=True, text=True, timeout=30)
            if build_result.returncode != 0:
                print(f"❌ Build failed: {build_result.stderr}")
                sys.exit(1)
            print("✓ Build successful")
        except Exception as e:
            print(f"❌ Build failed: {e}")
            sys.exit(1)
    
    success = test_mcp_workflow(args.server_binary)
    
    if success:
        print("\n🎉 STDIO integration test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ STDIO integration test FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()