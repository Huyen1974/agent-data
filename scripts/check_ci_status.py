#!/usr/bin/env python3
"""
Simple script to check CI status and get logs for analysis
"""

import subprocess
import json
import sys
import time
from datetime import datetime

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def check_workflow_status():
    """Check status of all workflows"""
    repo = "Huyen1974/agent-data"
    workflows = ["deploy_functions.yaml", "deploy_containers.yaml", "deploy_workflows.yaml"]
    
    print("🔍 Checking CI Status for Huyen1974/agent-data (main branch)")
    print("=" * 60)
    
    for workflow in workflows:
        print(f"\n📋 {workflow}:")
        
        # Get latest runs for this workflow
        cmd = f'gh run list --workflow={workflow} --repo {repo} --limit 3 --json status,conclusion,createdAt,databaseId'
        exit_code, stdout, stderr = run_command(cmd)
        
        if exit_code != 0:
            print(f"❌ Failed to get runs: {stderr}")
            continue
        
        try:
            runs = json.loads(stdout)
            if not runs:
                print("   No runs found")
                continue
                
            for i, run in enumerate(runs):
                status = run.get('status', 'unknown')
                conclusion = run.get('conclusion', 'N/A')
                created = run.get('createdAt', 'unknown')
                run_id = run.get('databaseId', 'unknown')
                
                status_emoji = "🟡" if status == "in_progress" else "🔴" if conclusion == "failure" else "🟢" if conclusion == "success" else "⚪"
                
                print(f"   {status_emoji} Run {i+1}: {status} / {conclusion} (ID: {run_id})")
                print(f"      Created: {created}")
                
                # If this is the latest run and it failed, get logs
                if i == 0 and conclusion == "failure":
                    print(f"      🔍 Getting failure logs...")
                    log_cmd = f'gh run view {run_id} --repo {repo} --log-failed'
                    log_exit, log_stdout, log_stderr = run_command(log_cmd)
                    
                    if log_exit == 0:
                        # Extract key error messages
                        lines = log_stdout.split('\n')
                        error_lines = [line for line in lines if any(keyword in line.lower() for keyword in ['error', 'failed', 'denied', 'invalid', 'missing'])]
                        
                        if error_lines:
                            print(f"      🚨 Key errors found:")
                            for error in error_lines[:5]:  # Show first 5 errors
                                print(f"         {error.strip()}")
                        else:
                            print(f"      📝 No obvious errors in logs")
                    else:
                        print(f"      ❌ Failed to get logs: {log_stderr}")
                        
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response: {stdout}")
    
    print("\n" + "=" * 60)
    print("✅ Status check complete")

if __name__ == "__main__":
    check_workflow_status() 