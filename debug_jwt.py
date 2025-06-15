#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from src.agent_data_manager.auth.auth_manager import AuthManager
import time

print("=== Testing AuthManager JWT implementation ===")

# Initialize AuthManager
auth_manager = AuthManager()

# Test 1: Create a token that should be valid immediately
print("\n=== Test 1: Valid token ===")
token_data = {"sub": "test_user", "email": "test@example.com"}
token = auth_manager.create_access_token(token_data, expires_delta=timedelta(seconds=10))

print(f"Created token: {token[:50]}...")

try:
    payload = auth_manager.verify_token(token)
    print(f"✓ Token verified successfully: {payload}")
except Exception as e:
    print(f"✗ Token verification failed: {e}")

# Test 2: Create an expired token
print("\n=== Test 2: Expired token ===")
expired_token = auth_manager.create_access_token(token_data, expires_delta=timedelta(seconds=-1))

try:
    payload = auth_manager.verify_token(expired_token)
    print(f"✗ Expired token should have failed but passed: {payload}")
except Exception as e:
    print(f"✓ Expired token correctly rejected: {e}")

# Test 3: Test timing precision
print("\n=== Test 3: Timing precision test ===")
for i in range(3):
    print(f"Attempt {i+1}:")
    token = auth_manager.create_access_token(token_data, expires_delta=timedelta(seconds=2))
    
    try:
        payload = auth_manager.verify_token(token)
        print(f"  ✓ Immediate verification successful")
        
        # Wait and try again
        time.sleep(1)
        payload = auth_manager.verify_token(token)
        print(f"  ✓ Verification after 1s still successful")
        
        # Wait for expiration
        time.sleep(2)
        payload = auth_manager.verify_token(token)
        print(f"  ✗ Token should have expired but didn't")
        
    except Exception as e:
        if "expired" in str(e).lower():
            print(f"  ✓ Token correctly expired: {e}")
        else:
            print(f"  ✗ Unexpected error: {e}")
    
    print() 