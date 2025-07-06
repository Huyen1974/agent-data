#!/usr/bin/env python3
"""
Check repository secrets and service account configuration
"""

import subprocess
import json
import sys

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def check_secrets():
    """Check repository secrets"""
    repo = "Huyen1974/agent-data"
    
    print("🔐 Checking Repository Secrets")
    print("=" * 40)
    
    # Get secrets list
    cmd = f'gh secret list --repo {repo}'
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"❌ Failed to get secrets: {stderr}")
        return
    
    secrets = stdout.strip().split('\n')
    print(f"📋 Found {len(secrets)} secrets:")
    
    for secret in secrets:
        if secret.strip():
            print(f"   🔑 {secret}")
    
    # Check for required secrets
    required_secrets = ['GCP_SERVICE_ACCOUNT', 'GCP_WORKLOAD_ID_PROVIDER', 'PROJECT_ID']
    secret_names = [line.split()[0] for line in secrets if line.strip()]
    
    print(f"\n🔍 Required Secrets Status:")
    for required in required_secrets:
        status = "✅" if required in secret_names else "❌"
        print(f"   {status} {required}")
    
    # If GCP_SERVICE_ACCOUNT exists, try to extract the service account email
    if 'GCP_SERVICE_ACCOUNT' in secret_names:
        print(f"\n🔍 Service Account Analysis:")
        print(f"   The GCP_SERVICE_ACCOUNT secret exists but we cannot view its contents.")
        print(f"   Based on the error logs, the service account is missing the 'Service Account Token Creator' role.")
        print(f"   Expected service account: chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com")
        print(f"   Required role: roles/iam.serviceAccountTokenCreator")

if __name__ == "__main__":
    check_secrets() 