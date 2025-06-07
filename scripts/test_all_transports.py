#!/usr/bin/env python3
"""
All Transports Integration Test Script for MCP DevPod Server
This script tests all transport methods (STDIO, SSE, HTTP Streams) for the DevPod MCP server.
"""

import subprocess
import sys
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_test_script(script_name, args=None):
    """Run a test script and return the result"""
    if args is None:
        args = []
    
    cmd = ['python3', script_name] + args
    print(f"🚀 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per test
        )
        
        return {
            'script': script_name,
            'args': args,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            'script': script_name,
            'args': args,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Test timed out after 2 minutes',
            'success': False
        }
    except Exception as e:
        return {
            'script': script_name,
            'args': args,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }

def test_stdio():
    """Test STDIO transport"""
    return run_test_script('scripts/test_stdio_integration.py')

def test_sse():
    """Test SSE transport"""
    return run_test_script('scripts/test_sse_integration.py', ['--port', '8081'])

def test_http_streams():
    """Test HTTP Streams transport"""
    return run_test_script('scripts/test_http_streams_integration.py', ['--port', '8082'])

def test_devpod_functionality():
    """Test DevPod functionality across all transports"""
    return run_test_script('test_devpod_mcp.py')

def print_test_result(result):
    """Print formatted test result"""
    script = result['script']
    args = ' '.join(result['args']) if result['args'] else ''
    status = "✅ PASSED" if result['success'] else "❌ FAILED"
    
    print(f"\n{'='*60}")
    print(f"📋 Test: {script} {args}")
    print(f"🎯 Status: {status}")
    print(f"🔢 Exit Code: {result['returncode']}")
    
    if result['stdout']:
        print(f"\n📤 STDOUT:")
        print(result['stdout'])
    
    if result['stderr']:
        print(f"\n📥 STDERR:")
        print(result['stderr'])
    
    print(f"{'='*60}")

def main():
    """Main test function - runs all transport tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test all transports for DevPod MCP Server")
    parser.add_argument("--transport", choices=['stdio', 'sse', 'http-streams', 'devpod', 'all'], 
                       default='all', help="Which transport(s) to test")
    parser.add_argument("--parallel", action="store_true", 
                       help="Run tests in parallel (faster but harder to debug)")
    parser.add_argument("--verbose", action="store_true", 
                       help="Show detailed output from each test")
    
    args = parser.parse_args()
    
    print("🧪 Starting All Transports Integration Test for DevPod MCP Server")
    print(f"🎯 Testing: {args.transport}")
    print(f"⚡ Parallel: {args.parallel}")
    print()
    
    # Build the server first
    print("🔨 Building DevPod MCP server...")
    try:
        build_result = subprocess.run(['go', 'build', '-o', 'mcp-server-devpod', 'main.go'], 
                                    capture_output=True, text=True, timeout=60)
        if build_result.returncode != 0:
            print(f"❌ Build failed: {build_result.stderr}")
            sys.exit(1)
        print("✓ Build successful")
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)
    
    # Define test functions
    tests = []
    if args.transport in ['stdio', 'all']:
        tests.append(('STDIO', test_stdio))
    if args.transport in ['sse', 'all']:
        tests.append(('SSE', test_sse))
    if args.transport in ['http-streams', 'all']:
        tests.append(('HTTP Streams', test_http_streams))
    if args.transport in ['devpod', 'all']:
        tests.append(('DevPod Functionality', test_devpod_functionality))
    
    results = []
    
    if args.parallel and len(tests) > 1:
        # Run tests in parallel
        print(f"🚀 Running {len(tests)} tests in parallel...")
        
        with ThreadPoolExecutor(max_workers=len(tests)) as executor:
            # Submit all tests
            future_to_test = {executor.submit(test_func): test_name for test_name, test_func in tests}
            
            # Collect results as they complete
            for future in as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    result = future.result()
                    result['test_name'] = test_name
                    results.append(result)
                    
                    if args.verbose:
                        print_test_result(result)
                    else:
                        status = "✅ PASSED" if result['success'] else "❌ FAILED"
                        print(f"📋 {test_name}: {status}")
                        
                except Exception as e:
                    print(f"❌ {test_name} failed with exception: {e}")
                    results.append({
                        'test_name': test_name,
                        'script': 'unknown',
                        'args': [],
                        'returncode': -1,
                        'stdout': '',
                        'stderr': str(e),
                        'success': False
                    })
    else:
        # Run tests sequentially
        print(f"🚀 Running {len(tests)} tests sequentially...")
        
        for test_name, test_func in tests:
            print(f"\n📋 Starting {test_name} test...")
            result = test_func()
            result['test_name'] = test_name
            results.append(result)
            
            if args.verbose:
                print_test_result(result)
            else:
                status = "✅ PASSED" if result['success'] else "❌ FAILED"
                print(f"📋 {test_name}: {status}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"📋 {result['test_name']}: {status}")
    
    print(f"\n🎯 Total: {len(results)} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n❌ SOME TESTS FAILED!")
        print("🔍 Failed test details:")
        for result in results:
            if not result['success']:
                print(f"\n📋 {result['test_name']}:")
                print(f"   Script: {result['script']}")
                print(f"   Exit Code: {result['returncode']}")
                if result['stderr']:
                    print(f"   Error: {result['stderr'][:200]}...")
        sys.exit(1)
    else:
        print(f"\n🎉 ALL TESTS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main()