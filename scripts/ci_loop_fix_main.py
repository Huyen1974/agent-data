#!/usr/bin/env python3
"""
CLI 153.3 - Automated CI Loop Fix for Main Branch
Automatically check CI logs, identify errors, and fix them with up to 5 retry attempts.
"""

import os
import sys
import time
import json
import subprocess
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

class CILoopFixer:
    def __init__(self):
        self.repo = "Huyen1974/agent-data"
        self.branch = "main"
        self.max_attempts = 5
        self.current_attempt = 0
        self.workflows = [
            "Deploy to Google Cloud Functions",
            "Deploy Containers to Cloud Run", 
            "Deploy Cloud Workflows"
        ]
        self.memory_log_path = ".cursor/memory_log/ci_loop_fix_main.md"
        
    def log_to_memory(self, content: str):
        """Append content to memory log file"""
        try:
            with open(self.memory_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{content}")
        except Exception as e:
            print(f"Warning: Could not write to memory log: {e}")
    
    def run_command(self, cmd: str) -> Tuple[int, str, str]:
        """Run shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timeout"
        except Exception as e:
            return 1, "", str(e)
    
    def get_latest_runs(self) -> List[Dict]:
        """Get latest CI runs for the repository"""
        cmd = f'gh api repos/{self.repo}/actions/runs --jq \'.workflow_runs[:10] | .[] | {{status: .status, conclusion: .conclusion, name: .name, created_at: .created_at, id: .id, head_branch: .head_branch}}\''
        
        exit_code, stdout, stderr = self.run_command(cmd)
        if exit_code != 0:
            self.log_to_memory(f"❌ Failed to get CI runs: {stderr}")
            return []
        
        runs = []
        for line in stdout.strip().split('\n'):
            if line.strip():
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        # Filter for main branch and target workflows
        main_runs = [
            run for run in runs 
            if run.get('head_branch') == self.branch and 
               run.get('name') in self.workflows
        ]
        
        return main_runs
    
    def get_run_logs(self, run_id: str) -> str:
        """Get logs for a specific run"""
        cmd = f'gh api repos/{self.repo}/actions/runs/{run_id}/logs'
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            return f"Failed to get logs: {stderr}"
        
        return stdout
    
    def analyze_failure_patterns(self, logs: str) -> List[str]:
        """Analyze logs to identify failure patterns"""
        patterns = []
        
        # Check for secret validation failures
        if "GCP_SERVICE_ACCOUNT secret is missing" in logs:
            patterns.append("missing_service_account_secret")
        elif "GCP_WORKLOAD_ID_PROVIDER secret is missing" in logs:
            patterns.append("missing_workload_identity_secret")
        elif "PROJECT_ID secret is missing" in logs:
            patterns.append("missing_project_id_secret")
        
        # Check for authentication failures
        if "invalid JSON" in logs.lower():
            patterns.append("invalid_json_secret")
        elif "permission denied" in logs.lower():
            patterns.append("permission_denied")
        elif "iam.serviceAccounts.getAccessToken" in logs:
            patterns.append("missing_token_creator_role")
        elif "authentication failed" in logs.lower():
            patterns.append("auth_failure")
        
        # Check for Git failures
        if "exit code 128" in logs:
            patterns.append("git_failure")
        elif "fatal: could not read" in logs.lower():
            patterns.append("git_auth_failure")
        
        # Check for resource failures
        if "quota exceeded" in logs.lower():
            patterns.append("quota_exceeded")
        elif "timeout" in logs.lower():
            patterns.append("timeout")
        elif "not found" in logs.lower() and "project" in logs.lower():
            patterns.append("project_not_found")
        
        if not patterns:
            patterns.append("unknown_failure")
        
        return patterns
    
    def suggest_fixes(self, patterns: List[str]) -> List[str]:
        """Suggest fixes based on failure patterns"""
        fixes = []
        
        for pattern in patterns:
            if pattern == "missing_service_account_secret":
                fixes.append("Configure GCP_SERVICE_ACCOUNT secret in repository settings")
            elif pattern == "missing_workload_identity_secret":
                fixes.append("Configure GCP_WORKLOAD_ID_PROVIDER secret in repository settings")
            elif pattern == "missing_project_id_secret":
                fixes.append("Configure PROJECT_ID secret in repository settings")
            elif pattern == "invalid_json_secret":
                fixes.append("Validate and re-upload GCP_SERVICE_ACCOUNT JSON secret")
            elif pattern == "missing_token_creator_role":
                fixes.append("Grant roles/iam.serviceAccountTokenCreator to the service account")
            elif pattern == "permission_denied":
                fixes.append("Check IAM permissions for the service account")
            elif pattern == "auth_failure":
                fixes.append("Verify Workload Identity Federation configuration")
            elif pattern == "git_failure":
                fixes.append("Check repository access and GitHub token permissions")
            elif pattern == "quota_exceeded":
                fixes.append("Check GCP quotas and request increases if needed")
            elif pattern == "timeout":
                fixes.append("Retry deployment - may be temporary network issue")
            elif pattern == "project_not_found":
                fixes.append("Verify PROJECT_ID matches existing GCP project")
            else:
                fixes.append("Review full logs for specific error details")
        
        return fixes
    
    def trigger_workflow(self, workflow_name: str) -> bool:
        """Trigger a specific workflow"""
        # Map workflow names to file names
        workflow_files = {
            "Deploy to Google Cloud Functions": "deploy_functions.yaml",
            "Deploy Containers to Cloud Run": "deploy_containers.yaml",
            "Deploy Cloud Workflows": "deploy_workflows.yaml"
        }
        
        workflow_file = workflow_files.get(workflow_name)
        if not workflow_file:
            self.log_to_memory(f"❌ Unknown workflow: {workflow_name}")
            return False
        
        cmd = f'gh workflow run {workflow_file} --repo {self.repo} --ref {self.branch}'
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code == 0:
            self.log_to_memory(f"✅ Successfully triggered: {workflow_name}")
            return True
        else:
            self.log_to_memory(f"❌ Failed to trigger {workflow_name}: {stderr}")
            return False
    
    def wait_for_completion(self, timeout_minutes: int = 10) -> List[Dict]:
        """Wait for workflows to complete and return results"""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        self.log_to_memory(f"⏳ Waiting up to {timeout_minutes} minutes for workflows to complete...")
        
        while time.time() - start_time < timeout_seconds:
            runs = self.get_latest_runs()
            
            # Check if we have recent runs for all workflows
            now = datetime.now(timezone.utc)
            recent_runs = [
                run for run in runs 
                if (now - datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))).total_seconds() < 600
            ]
            
            if len(recent_runs) >= len(self.workflows):
                completed_runs = [run for run in recent_runs if run['status'] == 'completed']
                if len(completed_runs) >= len(self.workflows):
                    return completed_runs
            
            time.sleep(30)  # Check every 30 seconds
        
        self.log_to_memory(f"⏰ Timeout waiting for workflows to complete")
        return self.get_latest_runs()
    
    def check_secrets_status(self) -> Dict[str, bool]:
        """Check if required secrets are configured"""
        cmd = f'gh secret list --repo {self.repo}'
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_to_memory(f"❌ Failed to check secrets: {stderr}")
            return {}
        
        secrets = stdout.lower()
        required_secrets = [
            'gcp_service_account',
            'gcp_workload_id_provider', 
            'project_id'
        ]
        
        secret_status = {}
        for secret in required_secrets:
            secret_status[secret] = secret in secrets
        
        return secret_status
    
    def run_loop_attempt(self) -> bool:
        """Run a single loop attempt"""
        self.current_attempt += 1
        
        self.log_to_memory(f"\n### Loop {self.current_attempt} - Attempt {self.current_attempt}/{self.max_attempts}")
        self.log_to_memory(f"**Time**: {datetime.now().isoformat()}")
        
        # Check secrets status
        self.log_to_memory("\n#### Secrets Status Check")
        secret_status = self.check_secrets_status()
        for secret, exists in secret_status.items():
            status = "✅" if exists else "❌"
            self.log_to_memory(f"- {secret}: {status}")
        
        # Check current CI status
        self.log_to_memory("\n#### Current CI Status")
        recent_runs = self.get_latest_runs()
        
        if not recent_runs:
            self.log_to_memory("No recent CI runs found. Triggering workflows...")
        else:
            for run in recent_runs[:3]:  # Show last 3 runs
                status = run.get('conclusion', run.get('status', 'unknown'))
                self.log_to_memory(f"- {run['name']}: {status} ({run['created_at']})")
        
        # Trigger workflows
        self.log_to_memory("\n#### Triggering Workflows")
        triggered_count = 0
        for workflow in self.workflows:
            if self.trigger_workflow(workflow):
                triggered_count += 1
        
        if triggered_count == 0:
            self.log_to_memory("❌ Failed to trigger any workflows")
            return False
        
        # Wait for completion
        completed_runs = self.wait_for_completion()
        
        # Analyze results
        self.log_to_memory("\n#### Results Analysis")
        success_count = 0
        
        for run in completed_runs:
            workflow_name = run['name']
            conclusion = run.get('conclusion', 'unknown')
            
            if conclusion == 'success':
                success_count += 1
                self.log_to_memory(f"✅ {workflow_name}: SUCCESS")
            else:
                self.log_to_memory(f"❌ {workflow_name}: {conclusion}")
                
                # Get and analyze logs
                run_id = str(run['id'])
                logs = self.get_run_logs(run_id)
                patterns = self.analyze_failure_patterns(logs)
                fixes = self.suggest_fixes(patterns)
                
                self.log_to_memory(f"   Failure patterns: {', '.join(patterns)}")
                self.log_to_memory(f"   Suggested fixes:")
                for fix in fixes:
                    self.log_to_memory(f"   - {fix}")
        
        # Check if all workflows succeeded
        if success_count == len(self.workflows):
            self.log_to_memory(f"\n🎉 **SUCCESS**: All {len(self.workflows)} workflows completed successfully!")
            return True
        else:
            self.log_to_memory(f"\n⚠️  **PARTIAL SUCCESS**: {success_count}/{len(self.workflows)} workflows succeeded")
            return False
    
    def run(self):
        """Main execution loop"""
        print("🚀 Starting CLI 153.3 - CI Loop Fix for Main Branch")
        
        self.log_to_memory(f"\n## Loop Execution Started")
        self.log_to_memory(f"**Start Time**: {datetime.now().isoformat()}")
        self.log_to_memory(f"**Repository**: {self.repo}")
        self.log_to_memory(f"**Branch**: {self.branch}")
        self.log_to_memory(f"**Max Attempts**: {self.max_attempts}")
        
        while self.current_attempt < self.max_attempts:
            print(f"\n🔄 Running attempt {self.current_attempt + 1}/{self.max_attempts}")
            
            success = self.run_loop_attempt()
            
            if success:
                self.log_to_memory(f"\n## ✅ FINAL RESULT: SUCCESS")
                self.log_to_memory(f"**Attempts Used**: {self.current_attempt}/{self.max_attempts}")
                self.log_to_memory(f"**End Time**: {datetime.now().isoformat()}")
                print("✅ CI is now GREEN! All workflows completed successfully.")
                return True
            
            if self.current_attempt < self.max_attempts:
                wait_time = min(60 * (2 ** self.current_attempt), 300)  # Exponential backoff, max 5 minutes
                self.log_to_memory(f"\n⏳ Waiting {wait_time} seconds before next attempt...")
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        self.log_to_memory(f"\n## ❌ FINAL RESULT: FAILED")
        self.log_to_memory(f"**Attempts Used**: {self.current_attempt}/{self.max_attempts}")
        self.log_to_memory(f"**End Time**: {datetime.now().isoformat()}")
        print("❌ Maximum attempts reached. CI still has failures.")
        return False

if __name__ == "__main__":
    fixer = CILoopFixer()
    success = fixer.run()
    sys.exit(0 if success else 1) 