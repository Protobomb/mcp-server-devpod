#!/usr/bin/env python3
"""
Test script to use Ollama with our MCP DevPod server.
This script bridges Ollama's tool calling with our MCP server.
"""

import json
import subprocess
import time
import threading
import queue
import ollama
import sys
from typing import Dict, List, Any, Optional

class MCPServerBridge:
    def __init__(self, server_path: str = "./mcp-server-devpod"):
        self.server_path = server_path
        self.process = None
        self.request_id = 1
        
    def start_server(self):
        """Start the MCP server process"""
        print("Starting MCP server...")
        self.process = subprocess.Popen(
            [self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Wait a moment for server to start
        time.sleep(1)
        
        # Initialize the server
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ollama-bridge", "version": "0.1.0"}
            }
        }
        
        response = self._send_request(init_request)
        if response and "result" in response:
            print("✅ MCP server initialized successfully")
            return True
        else:
            print("❌ Failed to initialize MCP server")
            return False
    
    def _send_request(self, request: Dict) -> Optional[Dict]:
        """Send a request to the MCP server and get response"""
        if not self.process:
            return None
            
        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Read response
            response_str = self.process.stdout.readline()
            if response_str:
                return json.loads(response_str.strip())
        except Exception as e:
            print(f"Error communicating with MCP server: {e}")
        
        return None
    
    def get_tools(self) -> List[Dict]:
        """Get the list of available tools from the MCP server"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list",
            "params": {}
        }
        
        response = self._send_request(request)
        if response and "result" in response and "tools" in response["result"]:
            return response["result"]["tools"]
        return []
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call a specific tool with given arguments"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = self._send_request(request)
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            return {"error": response["error"]}
        return {"error": "No response from server"}
    
    def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()

def convert_mcp_tools_to_ollama(mcp_tools: List[Dict]) -> List[Dict]:
    """Convert MCP tool definitions to Ollama tool format"""
    ollama_tools = []
    
    for tool in mcp_tools:
        ollama_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("inputSchema", {})
            }
        }
        ollama_tools.append(ollama_tool)
    
    return ollama_tools

def execute_tool_calls(bridge: MCPServerBridge, tool_calls: List[Dict]) -> List[Dict]:
    """Execute the tool calls via the MCP server"""
    results = []
    
    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        tool_name = function.get("name")
        arguments = function.get("arguments", {})
        
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        
        print(f"🔧 Calling tool: {tool_name} with arguments: {arguments}")
        
        result = bridge.call_tool(tool_name, arguments)
        results.append({
            "tool_call_id": tool_call.get("id", "unknown"),
            "role": "tool",
            "content": json.dumps(result, indent=2)
        })
        
        print(f"📋 Result: {json.dumps(result, indent=2)}")
    
    return results

def main():
    # Start MCP server
    bridge = MCPServerBridge()
    
    try:
        if not bridge.start_server():
            print("Failed to start MCP server")
            return
        
        # Get available tools
        print("\n🔍 Getting available tools...")
        mcp_tools = bridge.get_tools()
        print(f"Found {len(mcp_tools)} tools:")
        for tool in mcp_tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Convert to Ollama format
        ollama_tools = convert_mcp_tools_to_ollama(mcp_tools)
        
        # Interactive chat loop
        print("\n💬 Starting interactive chat with Ollama + DevPod tools")
        print("Type 'quit' to exit")
        
        messages = []
        
        while True:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            try:
                print("🤖 Ollama is thinking...")
                
                # Call Ollama with tools
                response = ollama.chat(
                    model='llama3.2:3b',
                    messages=messages,
                    tools=ollama_tools
                )
                
                message = response.get('message', {})
                content = message.get('content', '')
                tool_calls = message.get('tool_calls', [])
                
                if content:
                    print(f"🤖 Ollama: {content}")
                    messages.append({"role": "assistant", "content": content})
                
                if tool_calls:
                    print(f"\n🔧 Ollama wants to use {len(tool_calls)} tool(s)")
                    
                    # Execute tool calls
                    tool_results = execute_tool_calls(bridge, tool_calls)
                    
                    # Add tool calls and results to conversation
                    messages.append({
                        "role": "assistant", 
                        "content": content,
                        "tool_calls": tool_calls
                    })
                    
                    for result in tool_results:
                        messages.append(result)
                    
                    # Get Ollama's response to the tool results
                    print("\n🤖 Ollama is processing tool results...")
                    follow_up = ollama.chat(
                        model='llama3.2:3b',
                        messages=messages
                    )
                    
                    follow_up_content = follow_up.get('message', {}).get('content', '')
                    if follow_up_content:
                        print(f"🤖 Ollama: {follow_up_content}")
                        messages.append({"role": "assistant", "content": follow_up_content})
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        bridge.stop_server()
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()