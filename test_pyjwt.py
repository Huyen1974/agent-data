#!/usr/bin/env python3

import jwt as pyjwt
from datetime import datetime, timedelta
import time

print("=== PyJWT Test ===")

secret = "test-secret"
current_time = datetime.utcnow()
future_time = current_time + timedelta(minutes=5)

print(f"Current UTC time: {current_time}")
print(f"Future UTC time: {future_time}")
print(f"Current timestamp: {int(current_time.timestamp())}")
print(f"Future timestamp: {int(future_time.timestamp())}")

# Create a simple token
payload = {
    "sub": "test_user",
    "exp": int(future_time.timestamp()),
    "iat": int(current_time.timestamp())
}

print(f"\nPayload: {payload}")

# Encode token
token = pyjwt.encode(payload, secret, algorithm="HS256")
print(f"Token: {token}")

# Decode without expiration check
try:
    decoded_no_exp = pyjwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
    print(f"Decoded (no exp check): {decoded_no_exp}")
except Exception as e:
    print(f"Decode failed (no exp check): {e}")

# Decode with expiration check
try:
    decoded_with_exp = pyjwt.decode(token, secret, algorithms=["HS256"])
    print(f"✓ Decoded (with exp check): {decoded_with_exp}")
except Exception as e:
    print(f"✗ Decode failed (with exp check): {e}")
    print(f"Error type: {type(e)}")

# Check PyJWT version
try:
    print(f"\nPyJWT version: {pyjwt.__version__}")
except:
    print("\nCould not get PyJWT version")

# Manual expiration check
print(f"\nManual expiration check:")
print(f"Token exp: {payload['exp']}")
print(f"Current time: {int(datetime.utcnow().timestamp())}")
print(f"Time difference: {payload['exp'] - int(datetime.utcnow().timestamp())} seconds")
print(f"Is expired: {payload['exp'] < int(datetime.utcnow().timestamp())}")

# Test immediate creation and verification
print(f"\n=== Immediate test ===")
for i in range(3):
    print(f"Test {i+1}:")
    immediate_payload = {
        "sub": "test_user",
        "exp": int((datetime.utcnow() + timedelta(seconds=30)).timestamp()),
        "iat": int(datetime.utcnow().timestamp())
    }
    
    immediate_token = pyjwt.encode(immediate_payload, secret, algorithm="HS256")
    
    try:
        immediate_decoded = pyjwt.decode(immediate_token, secret, algorithms=["HS256"])
        print(f"  ✓ Success: exp={immediate_decoded['exp']}, current={int(datetime.utcnow().timestamp())}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    
    time.sleep(0.1) 