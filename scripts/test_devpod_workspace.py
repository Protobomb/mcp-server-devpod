#!/usr/bin/env python3
"""
Test DevPod workspace operations via MCP
"""

import json
import requests
import threading
import time

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
        self.sse_thread = threading.Thread(target=self._listen_sse)
        self.sse_thread.daemon = True
        self.sse_thread.start()
        
        for _ in range(50):
            if self.connected:
                return True
            time.sleep(0.1)
        return False
    
    def _listen_sse(self):
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
                    data = line[6:]
                    if data.strip():
                        try:
                            message = json.loads(data)
                            self.responses.append(message)
                        except json.JSONDecodeError:
                            pass
                            
        except Exception as e:
            print(f"SSE connection error: {e}")
            self.connected = False
    
    def send_message(self, message):
        try:
            response = requests.post(
                self.message_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            return {"status": "accepted"}
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def wait_for_response(self, request_id=None, timeout=10):
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for i, response in enumerate(self.responses):
                if request_id is None or response.get('id') == request_id:
                    return self.responses.pop(i)
            time.sleep(0.1)
        return None
    
    def disconnect(self):
        self.stop_event.set()
        if self.sse_thread:
            self.sse_thread.join(timeout=2)

def test_workspace_operations():
    """Test DevPod workspace operations"""
    base_url = "http://172.17.0.6:8080"
    session_id = f"test-session-{int(time.time())}"
    
    print(f"🧪 Testing DevPod Workspace Operations")
    print(f"📡 Base URL: {base_url}")
    print()
    
    client = SSEClient(base_url, session_id)
    
    try:
        # Connect and initialize
        if not client.connect():
            print("❌ Failed to connect to SSE")
            return False
        
        # Initialize
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "workspace-test", "version": "1.0.0"}
            }
        }
        client.send_message(init_message)
        client.wait_for_response(request_id=1, timeout=5)
        
        # Initialized notification
        client.send_message({"jsonrpc": "2.0", "method": "initialized"})
        
        # Test 1: Check status of hello-world workspace
        print("📋 Test 1: Check hello-world workspace status")
        status_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "devpod_status",
                "arguments": {"name": "hello-world"}
            }
        }
        
        client.send_message(status_message)
        status_response = client.wait_for_response(request_id=2, timeout=10)
        if status_response:
            print(f"✓ Status response: {status_response}")
        else:
            print("❌ No status response")
        
        # Test 2: Try to start the workspace
        print("\n📋 Test 2: Try to start hello-world workspace")
        start_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "devpod_startWorkspace",
                "arguments": {"name": "hello-world"}
            }
        }
        
        client.send_message(start_message)
        start_response = client.wait_for_response(request_id=3, timeout=30)
        if start_response:
            print(f"✓ Start response: {start_response}")
        else:
            print("❌ No start response")
        
        # Test 3: Create a simple workspace with a minimal repo
        print("\n📋 Test 3: Create a simple workspace")
        create_message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "devpod_createWorkspace",
                "arguments": {
                    "name": "simple-test",
                    "source": "https://github.com/octocat/Hello-World"
                }
            }
        }
        
        client.send_message(create_message)
        create_response = client.wait_for_response(request_id=4, timeout=30)
        if create_response:
            print(f"✓ Create response: {create_response}")
            
            # Test 4: Check status of new workspace
            print("\n📋 Test 4: Check simple-test workspace status")
            status_message2 = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "devpod_status",
                    "arguments": {"name": "simple-test"}
                }
            }
            
            client.send_message(status_message2)
            status_response2 = client.wait_for_response(request_id=5, timeout=10)
            if status_response2:
                print(f"✓ Status response: {status_response2}")
        else:
            print("❌ No create response")
        
        print("\n" + "=" * 50)
        print("✅ Workspace operations testing completed!")
        return True
        
    finally:
        client.disconnect()

if __name__ == "__main__":
    test_workspace_operations()