#!/usr/bin/env python3
"""
Test MCP DevPod server using SSE protocol
"""

import json
import requests
import threading
import time
import sys

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
            self.connected = True
            
            for line in response.iter_lines(decode_unicode=True):
                if self.stop_event.is_set():
                    break
                    
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data.strip():
                        try:
                            message = json.loads(data)
                            self.responses.append(message)
                            print(f"📨 Received: {json.dumps(message, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"📨 Received non-JSON: {data}")
                            
        except Exception as e:
            print(f"SSE connection error: {e}")
            self.connected = False
    
    def send_message(self, message):
        """Send a message to the server"""
        try:
            response = requests.post(
                self.message_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
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
            for i, response in enumerate(self.responses):
                if request_id is None or response.get('id') == request_id:
                    return self.responses.pop(i)
            time.sleep(0.1)
        return None
    
    def disconnect(self):
        """Disconnect from SSE"""
        self.stop_event.set()
        if self.sse_thread:
            self.sse_thread.join(timeout=2)

def test_mcp_devpod():
    """Test MCP DevPod server"""
    # Use container IP
    base_url = "http://172.17.0.6:8080"
    session_id = f"test-session-{int(time.time())}"
    
    print(f"🧪 Testing MCP DevPod Server")
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
        
        print("✓ Connected to SSE")
        
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
        
        # Test 3: List tools
        print("\n📋 Test 3: List tools")
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print(f"→ Sending: {json.dumps(list_tools_message, indent=2)}")
        post_response = client.send_message(list_tools_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for response
        tools_response = client.wait_for_response(request_id=2, timeout=5)
        if tools_response and 'result' in tools_response:
            tools = tools_response['result'].get('tools', [])
            print(f"✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}")
        else:
            print(f"❌ List tools failed: {tools_response}")
            return False
        
        # Test 4: Echo tool
        print("\n📋 Test 4: Echo tool")
        echo_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "message": "Hello from MCP!"
                }
            }
        }
        
        print(f"→ Sending: {json.dumps(echo_message, indent=2)}")
        post_response = client.send_message(echo_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for response
        echo_response = client.wait_for_response(request_id=3, timeout=5)
        if echo_response and 'result' in echo_response:
            print(f"✓ Echo response: {echo_response['result']}")
        else:
            print(f"❌ Echo failed: {echo_response}")
        
        # Test 5: List workspaces
        print("\n📋 Test 5: List workspaces")
        list_workspaces_message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "devpod_listWorkspaces",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(list_workspaces_message, indent=2)}")
        post_response = client.send_message(list_workspaces_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for response
        workspaces_response = client.wait_for_response(request_id=4, timeout=5)
        if workspaces_response:
            print(f"✓ Workspaces response: {workspaces_response}")
        else:
            print(f"❌ List workspaces failed")
        
        # Test 6: List providers
        print("\n📋 Test 6: List providers")
        list_providers_message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "devpod_listProviders",
                "arguments": {}
            }
        }
        
        print(f"→ Sending: {json.dumps(list_providers_message, indent=2)}")
        post_response = client.send_message(list_providers_message)
        print(f"📤 POST response: {post_response}")
        
        # Wait for response
        providers_response = client.wait_for_response(request_id=5, timeout=5)
        if providers_response:
            print(f"✓ Providers response: {providers_response}")
        else:
            print(f"❌ List providers failed")
        
        print("\n" + "=" * 50)
        print("✅ MCP DevPod server testing completed successfully!")
        return True
        
    finally:
        client.disconnect()

if __name__ == "__main__":
    test_mcp_devpod()