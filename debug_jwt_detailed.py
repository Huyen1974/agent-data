#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from jose import jwt, JWTError
import time

print("=== Detailed JWT Debugging ===")

# Test system time
print(f"System time: {datetime.utcnow()}")
print(f"System timestamp: {datetime.utcnow().timestamp()}")

# Test basic JWT creation and verification
secret = "test-secret-key"
current_time = datetime.utcnow()
expire_time = current_time + timedelta(seconds=10)

print(f"\nCurrent time: {current_time}")
print(f"Expire time: {expire_time}")
print(f"Current timestamp: {int(current_time.timestamp())}")
print(f"Expire timestamp: {int(expire_time.timestamp())}")

# Create token with different buffer strategies
buffers = [0, 1, 5, 10, 30]

for buffer in buffers:
    print(f"\n=== Testing with {buffer}s buffer ===")
    
    token_data = {
        "sub": "test_user",
        "exp": int(expire_time.timestamp()) + buffer,
        "iat": int(current_time.timestamp())
    }
    
    print(f"Token exp: {token_data['exp']}")
    print(f"Token iat: {token_data['iat']}")
    print(f"Current time when creating: {int(datetime.utcnow().timestamp())}")
    
    token = jwt.encode(token_data, secret, algorithm="HS256")
    
    # Immediate verification
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        print(f"✓ Immediate verification successful")
        print(f"  Decoded exp: {payload['exp']}")
        print(f"  Current time during decode: {int(datetime.utcnow().timestamp())}")
        print(f"  Time difference: {payload['exp'] - int(datetime.utcnow().timestamp())}s")
    except JWTError as e:
        print(f"✗ Immediate verification failed: {e}")
        print(f"  Current time during decode: {int(datetime.utcnow().timestamp())}")
        print(f"  Expected exp: {token_data['exp']}")
        print(f"  Time difference: {token_data['exp'] - int(datetime.utcnow().timestamp())}s")

# Test with AuthManager
print(f"\n=== Testing AuthManager ===")
try:
    from src.agent_data_manager.auth.auth_manager import AuthManager
    
    auth_manager = AuthManager()
    
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    token_data = {"sub": "test_user", "email": "test@example.com"}
    token = auth_manager.create_access_token(token_data, expires_delta=timedelta(seconds=30))
    
    print(f"AuthManager token created: {token[:50]}...")
    
    # Decode manually to see what's inside
    try:
        payload = jwt.decode(token, auth_manager.secret_key, algorithms=[auth_manager.algorithm], options={"verify_exp": False})
        print(f"Token payload (no exp check): {payload}")
        print(f"Token exp: {payload.get('exp')}")
        print(f"Current time: {int(datetime.utcnow().timestamp())}")
        print(f"Time until expiry: {payload.get('exp', 0) - int(datetime.utcnow().timestamp())}s")
    except Exception as e:
        print(f"Manual decode failed: {e}")
    
    # Try verification
    try:
        verified_payload = auth_manager.verify_token(token)
        print(f"✓ AuthManager verification successful: {verified_payload}")
    except Exception as e:
        print(f"✗ AuthManager verification failed: {e}")
        
except ImportError as e:
    print(f"Could not import AuthManager: {e}") 