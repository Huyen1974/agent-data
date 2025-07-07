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

def get_recent_runs(workflow_name, limit=3):
    """Get recent workflow runs"""
    cmd = [
        'gh', 'run', 'list', 
        '--workflow', workflow_name,
        '--repo', 'Huyen1974/agent-data',
        '--limit', str(limit),
        '--json', 'status,conclusion,createdAt,databaseId,headBranch,displayTitle'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting runs for {workflow_name}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for {workflow_name}: {e}")
        return []

def main():
    workflows = ['ci.yml', 'deploy_functions.yaml', 'deploy_containers.yaml', 'deploy_workflows.yaml']
    
    print("🔍 CLI 154.6 Main Branch CI Status")
    print("=" * 50)
    
    for workflow in workflows:
        print(f"\n📋 {workflow}:")
        runs = get_recent_runs(workflow, 2)
        
        if not runs:
            print("   No runs found")
            continue
            
        # Filter for main branch runs
        main_runs = [run for run in runs if run.get('headBranch') == 'main']
        
        if not main_runs:
            print("   No main branch runs found")
            continue
            
        for i, run in enumerate(main_runs):
            status = run.get('status', 'unknown')
            conclusion = run.get('conclusion', 'N/A')
            created = run.get('createdAt', 'unknown')
            run_id = run.get('databaseId', 'unknown')
            title = run.get('displayTitle', 'N/A')
            
            status_emoji = '🟡' if status == 'in_progress' else '🔴' if conclusion == 'failure' else '🟢' if conclusion == 'success' else '⚪'
            
            print(f"   {status_emoji} Run {i+1}: {status}/{conclusion} (ID: {run_id})")
            print(f"      Title: {title}")
            print(f"      Created: {created}")

if __name__ == "__main__":
    main() 