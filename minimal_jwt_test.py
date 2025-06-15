#!/usr/bin/env python3

from jose import jwt, JWTError
from datetime import datetime, timedelta
import time

print("=== Minimal JWT Test ===")

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
token = jwt.encode(payload, secret, algorithm="HS256")
print(f"Token: {token}")

# Decode without expiration check
try:
    decoded_no_exp = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
    print(f"Decoded (no exp check): {decoded_no_exp}")
except Exception as e:
    print(f"Decode failed (no exp check): {e}")

# Decode with expiration check
try:
    decoded_with_exp = jwt.decode(token, secret, algorithms=["HS256"])
    print(f"Decoded (with exp check): {decoded_with_exp}")
except JWTError as e:
    print(f"Decode failed (with exp check): {e}")
    print(f"Error type: {type(e)}")

# Check jose library version
try:
    import jose
    print(f"\nJose version: {jose.__version__}")
except:
    print("\nCould not get jose version")

# Manual expiration check
print(f"\nManual expiration check:")
print(f"Token exp: {payload['exp']}")
print(f"Current time: {int(datetime.utcnow().timestamp())}")
print(f"Time difference: {payload['exp'] - int(datetime.utcnow().timestamp())} seconds")
print(f"Is expired: {payload['exp'] < int(datetime.utcnow().timestamp())}")

# Test with different algorithms
algorithms = ["HS256", "HS384", "HS512"]
for alg in algorithms:
    print(f"\n=== Testing with {alg} ===")
    try:
        token_alg = jwt.encode(payload, secret, algorithm=alg)
        decoded_alg = jwt.decode(token_alg, secret, algorithms=[alg])
        print(f"✓ {alg} works")
    except Exception as e:
        print(f"✗ {alg} failed: {e}") 