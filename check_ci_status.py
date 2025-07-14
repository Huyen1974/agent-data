#!/usr/bin/env python3
import subprocess
import json
import time
import sys

def get_latest_ci_run():
    """Get the latest CI workflow run for our commit."""
    commit_sha = "86e526604a37e58e2586364b310afd2c777c4633"  # Docker-based testing workflow SHA (debug improved)
    
    # Use GitHub CLI to get workflow runs
    cmd = [
        "gh", "api", 
        "repos/Huyen1974/agent-data/actions/runs",
        "--method", "GET",
        "--field", "per_page=10"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
            
        data = json.loads(result.stdout)
        
        # Find CI workflow runs for our commit
        for run in data.get('workflow_runs', []):
            if (run.get('head_sha') == commit_sha and 
                'ci.yml' in run.get('path', '')):
                return run
                
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def check_run_status(run_id):
    """Check the status of a specific run."""
    cmd = ["gh", "api", f"repos/Huyen1974/agent-data/actions/runs/{run_id}"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
            
        data = json.loads(result.stdout)
        return data.get('status'), data.get('conclusion')
    except:
        return None, None

def main():
    print("Looking for CI run...")
    max_attempts = 30  # Wait up to 5 minutes
    attempt = 0
    
    while attempt < max_attempts:
        run = get_latest_ci_run()
        
        if not run:
            print(f"❌ No CI run found for our commit yet (attempt {attempt + 1})")
            attempt += 1
            time.sleep(10)
            continue
            
        run_id = run['id']
        print(f"✅ Found CI run: {run_id}")
        print(f"Status: {run.get('status')}")
        print(f"Conclusion: {run.get('conclusion')}")
        
        # Watch the run
        while True:
            result = check_run_status(run_id)
            if result is None or len(result) != 2:
                print("❌ Error checking run status")
                break
            status, conclusion = result
                
            print(f"Status: {status}, Conclusion: {conclusion}")
            
            if status == 'completed':
                if conclusion == 'success':
                    print("🎉 CI run succeeded!")
                    return True
                else:
                    print(f"❌ CI run failed with conclusion: {conclusion}")
                    return False
                    
            time.sleep(10)  # Wait 10 seconds before checking again

    print("❌ Timeout waiting for CI run to start")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 