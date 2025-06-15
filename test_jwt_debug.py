#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from src.agent_data_manager.auth.auth_manager import AuthManager
import time
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

print("=== JWT Expiration Debug ===")

# Initialize AuthManager
auth_manager = AuthManager()

# Test data
user_data = {"sub": "test@cursor.integration", "email": "test@cursor.integration"}

# Create token with short expiration
short_expiry = timedelta(seconds=1)
short_token = auth_manager.create_access_token(user_data, expires_delta=short_expiry)

print(f"Created token with 1s expiry: {short_token[:50]}...")

# Decode token to see what's inside
from jose import jwt
payload_no_verify = jwt.decode(short_token, auth_manager.secret_key, algorithms=["HS256"], options={"verify_exp": False})
print(f"Token payload: {payload_no_verify}")
print(f"Token exp: {payload_no_verify['exp']}")
print(f"Current time: {int(time.time())}")
print(f"Time until expiry: {payload_no_verify['exp'] - int(time.time())}s")

# Verify immediately
try:
    payload = auth_manager.verify_token(short_token)
    print(f"✓ Immediate verification successful: {payload['sub']}")
except Exception as e:
    print(f"✗ Immediate verification failed: {e}")
    print(f"Exception type: {type(e)}")

# Wait for expiration
print("Waiting 1.5 seconds for token to expire...")
time.sleep(1.5)

print(f"After sleep - Current time: {int(time.time())}")
print(f"Token exp: {payload_no_verify['exp']}")
print(f"Is expired: {payload_no_verify['exp'] < int(time.time())}")

# Try to verify expired token
print("Verifying expired token...")
try:
    payload = auth_manager.verify_token(short_token)
    print(f"✗ Expired token verification should have failed but passed: {payload}")
except Exception as e:
    print(f"✓ Expired token correctly rejected: {e}")
    print(f"Exception type: {type(e)}")
    
    # Check if it's HTTPException
    from fastapi import HTTPException
    if isinstance(e, HTTPException):
        print(f"✓ Correct exception type (HTTPException) with status: {e.status_code}")
    else:
        print(f"✗ Wrong exception type, expected HTTPException")

# Test direct jose library call with same token
print(f"\n=== Direct jose test with same token ===")
from jose import jwt, JWTError

try:
    direct_payload = jwt.decode(short_token, auth_manager.secret_key, algorithms=["HS256"])
    print(f"✗ Direct jose verification should have failed but passed: {direct_payload}")
except JWTError as e:
    print(f"✓ Direct jose verification correctly failed: {e}")
    print(f"JWTError type: {type(e)}")

# Test with options to see if expiration is being ignored
try:
    no_exp_payload = jwt.decode(short_token, auth_manager.secret_key, algorithms=["HS256"], options={"verify_exp": False})
    print(f"No exp check payload: {no_exp_payload}")
except JWTError as e:
    print(f"No exp check failed: {e}")

# Check jose library configuration
print(f"\n=== Jose library info ===")
import jose
print(f"Jose version: {jose.__version__}")

# Test with explicit options
try:
    explicit_payload = jwt.decode(short_token, auth_manager.secret_key, algorithms=["HS256"], options={"verify_exp": True})
    print(f"✗ Explicit exp verification should have failed but passed: {explicit_payload}")
except JWTError as e:
    print(f"✓ Explicit exp verification correctly failed: {e}")

# Test with manual token creation to see raw jose behavior
print(f"\n=== Manual jose test ===")
from jose import jwt, JWTError
import time as time_module

current_ts = int(time_module.time())
exp_ts = current_ts + 1

manual_payload = {
    "sub": "test_user",
    "exp": exp_ts,
    "iat": current_ts
}

manual_token = jwt.encode(manual_payload, auth_manager.secret_key, algorithm="HS256")
print(f"Manual token created with exp={exp_ts}, current={current_ts}")

# Immediate verification
try:
    decoded = jwt.decode(manual_token, auth_manager.secret_key, algorithms=["HS256"])
    print(f"✓ Manual immediate verification successful")
except JWTError as e:
    print(f"✗ Manual immediate verification failed: {e}")

# Wait and try again
time.sleep(1.5)
print(f"After sleep, current time: {int(time_module.time())}")

try:
    decoded = jwt.decode(manual_token, auth_manager.secret_key, algorithms=["HS256"])
    print(f"✗ Manual expired verification should have failed but passed")
except JWTError as e:
    print(f"✓ Manual expired verification correctly failed: {e}")
    print(f"JWTError type: {type(e)}") 