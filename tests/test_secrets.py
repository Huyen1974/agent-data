"""
Test suite to verify required environment variables are present.
"""

import os
import pytest


class TestSecrets:
    """Test required environment variables are available."""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("env_var", [
        "OPENAI_API_KEY",
        "QDRANT_API_KEY", 
        "JWT_SECRET_KEY",
        "GCP_SERVICE_ACCOUNT",
        "GCP_WORKLOAD_IDENTITY_PROVIDER",
        "PROJECT_ID"
    ])
    def test_environment_variable_present(self, env_var):
        """Test that required environment variables are set."""
        value = os.environ.get(env_var)
        assert value is not None, f"Environment variable {env_var} not set"
        assert value != "", f"Environment variable {env_var} is empty"
        print(f"✅ {env_var}: {'*' * min(len(value), 10)}...")
    
    @pytest.mark.unit 
    def test_openai_api_key_format(self):
        """Test OpenAI API key has reasonable format."""
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY not set"
        # Accept both real keys (sk-) and dummy values for testing
        assert api_key in ["dummy"] or api_key.startswith("sk-"), \
            f"OPENAI_API_KEY should start with 'sk-' or be 'dummy', got: {api_key[:10]}..."
        print(f"✅ OPENAI_API_KEY format valid: {api_key[:10]}...")
    
    @pytest.mark.unit
    def test_jwt_secret_key_length(self):
        """Test JWT secret key has minimum length for security."""
        jwt_key = os.environ.get("JWT_SECRET_KEY")
        assert jwt_key is not None, "JWT_SECRET_KEY not set"
        assert len(jwt_key) >= 32, \
            f"JWT_SECRET_KEY should be at least 32 characters, got {len(jwt_key)}"
        print(f"✅ JWT_SECRET_KEY length: {len(jwt_key)} characters")
    
    @pytest.mark.unit
    def test_gcp_workload_identity_provider_format(self):
        """Test GCP Workload Identity Provider has correct format."""
        wip = os.environ.get("GCP_WORKLOAD_IDENTITY_PROVIDER")
        assert wip is not None, "GCP_WORKLOAD_IDENTITY_PROVIDER not set"
        assert wip.startswith("projects/"), \
            f"GCP_WORKLOAD_IDENTITY_PROVIDER should start with 'projects/', got: {wip[:20]}..."
        assert "workloadIdentityPools" in wip, \
            f"GCP_WORKLOAD_IDENTITY_PROVIDER should contain 'workloadIdentityPools', got: {wip[:50]}..."
        print(f"✅ GCP_WORKLOAD_IDENTITY_PROVIDER format valid")
    
    @pytest.mark.unit
    def test_required_secrets_count(self):
        """Test that all 6 required secrets are present."""
        required_secrets = [
            "OPENAI_API_KEY",
            "QDRANT_API_KEY", 
            "JWT_SECRET_KEY",
            "GCP_SERVICE_ACCOUNT",
            "GCP_WORKLOAD_IDENTITY_PROVIDER",
            "PROJECT_ID"
        ]
        
        present_secrets = []
        for secret in required_secrets:
            if os.environ.get(secret):
                present_secrets.append(secret)
        
        assert len(present_secrets) == len(required_secrets), \
            f"Expected {len(required_secrets)} secrets, found {len(present_secrets)}: {present_secrets}"
        
        print(f"✅ All {len(present_secrets)} required secrets present: {required_secrets}") 