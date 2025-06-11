"""
Cloud Function for automated task report updates via GitHub API.
Updates task_report.md with latest task progress and completion status.
Enhanced with CI/CD run data fetching for CLI 135.
"""

import json
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import functions_framework
import requests
from google.cloud import firestore
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "chatgpt-db-project"
GITHUB_REPO_OWNER = "nmhuyen"  # Update with actual GitHub username
GITHUB_REPO_NAME = "mpc_back_end_for_agents"  # Update with actual repo name
TASK_REPORT_PATH = "task_report.md"
GITHUB_TOKEN_SECRET = "github-token"  # Secret Manager secret name


def get_github_token() -> str:
    """
    Retrieve GitHub token from Secret Manager.

    Returns:
        GitHub personal access token
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{PROJECT_ID}/secrets/{GITHUB_TOKEN_SECRET}/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to get GitHub token: {e}")
        raise


def get_github_ci_runs(github_token: str, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Fetch recent CI/CD workflow runs from GitHub API.

    Args:
        github_token: GitHub personal access token
        limit: Number of recent runs to fetch

    Returns:
        List of workflow run data
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/runs"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

        params = {"per_page": limit, "status": "completed"}  # Only get completed runs

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            runs = []

            for run in data.get("workflow_runs", []):
                run_data = {
                    "id": run.get("id"),
                    "name": run.get("name"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "created_at": run.get("created_at"),
                    "updated_at": run.get("updated_at"),
                    "run_number": run.get("run_number"),
                    "workflow_id": run.get("workflow_id"),
                    "head_branch": run.get("head_branch"),
                    "head_sha": run.get("head_sha")[:8] if run.get("head_sha") else None,
                    "html_url": run.get("html_url"),
                }

                # Calculate duration if both timestamps exist
                if run.get("created_at") and run.get("updated_at"):
                    try:
                        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                        updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                        duration = (updated - created).total_seconds()
                        run_data["duration_seconds"] = int(duration)
                        run_data["duration_minutes"] = round(duration / 60, 2)
                    except Exception:
                        run_data["duration_seconds"] = None
                        run_data["duration_minutes"] = None

                runs.append(run_data)

            logger.info(f"Fetched {len(runs)} CI runs from GitHub API")
            return runs

        else:
            logger.error(f"Failed to fetch CI runs: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        logger.error(f"Failed to get GitHub CI runs: {e}")
        return []


def get_nightly_ci_stats(ci_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze nightly CI runs for performance statistics.

    Args:
        ci_runs: List of CI run data

    Returns:
        Dictionary with nightly CI statistics
    """
    nightly_runs = [run for run in ci_runs if "nightly" in run.get("name", "").lower()]

    if not nightly_runs:
        return {
            "total_nightly_runs": 0,
            "avg_duration_minutes": 0,
            "last_nightly_status": "unknown",
            "under_5_minutes": False,
        }

    total_duration = 0
    valid_durations = 0

    for run in nightly_runs:
        if run.get("duration_minutes") is not None:
            total_duration += run["duration_minutes"]
            valid_durations += 1

    avg_duration = total_duration / valid_durations if valid_durations > 0 else 0

    return {
        "total_nightly_runs": len(nightly_runs),
        "avg_duration_minutes": round(avg_duration, 2),
        "last_nightly_status": nightly_runs[0].get("conclusion", "unknown") if nightly_runs else "unknown",
        "under_5_minutes": avg_duration < 5.0 if avg_duration > 0 else False,
        "recent_runs": nightly_runs[:3],  # Last 3 nightly runs
    }


def _format_ci_runs_table(runs: List[Dict[str, Any]]) -> str:
    """
    Format CI runs data into a markdown table.

    Args:
        runs: List of CI run data

    Returns:
        Formatted markdown table
    """
    if not runs:
        return "No recent CI runs available."

    table = "| Run # | Workflow | Status | Duration | Branch | SHA | Date |\n"
    table += "|-------|----------|--------|----------|--------|-----|------|\n"

    for run in runs:
        run_num = run.get("run_number", "N/A")
        name = run.get("name", "Unknown")[:20]  # Truncate long names
        status = "✅" if run.get("conclusion") == "success" else "❌" if run.get("conclusion") == "failure" else "⏸️"
        duration = f"{run.get('duration_minutes', 0):.1f}m" if run.get("duration_minutes") else "N/A"
        branch = run.get("head_branch", "unknown")[:10]  # Truncate long branch names
        sha = run.get("head_sha", "unknown")

        # Format date
        date_str = "N/A"
        if run.get("created_at"):
            try:
                date_obj = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                date_str = date_obj.strftime("%m/%d")
            except Exception:
                pass

        table += f"| {run_num} | {name} | {status} | {duration} | {branch} | {sha} | {date_str} |\n"

    return table


def get_firestore_stats() -> Dict[str, Any]:
    """
    Get statistics from Firestore collections.

    Returns:
        Dictionary with collection statistics
    """
    try:
        db = firestore.Client(project=PROJECT_ID)
        stats = {}

        # Document metadata stats
        doc_metadata_ref = db.collection("document_metadata")
        docs = list(doc_metadata_ref.stream())

        stats["document_metadata"] = {
            "total_documents": len(docs),
            "vectorized_documents": 0,
            "pending_documents": 0,
            "failed_documents": 0,
            "auto_tagged_documents": 0,
        }

        for doc in docs:
            data = doc.to_dict()
            vector_status = data.get("vectorStatus", "unknown")

            if vector_status == "completed":
                stats["document_metadata"]["vectorized_documents"] += 1
            elif vector_status == "pending":
                stats["document_metadata"]["pending_documents"] += 1
            elif vector_status == "failed":
                stats["document_metadata"]["failed_documents"] += 1

            if data.get("auto_tags"):
                stats["document_metadata"]["auto_tagged_documents"] += 1

        # Change reports stats
        try:
            change_reports_ref = db.collection("change_reports")
            change_docs = list(change_reports_ref.stream())
            stats["change_reports"] = {"total_reports": len(change_docs), "recent_reports": 0}

            # Count reports from last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            for doc in change_docs:
                data = doc.to_dict()
                generated_at = data.get("generated_at")
                if generated_at:
                    try:
                        report_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                        if report_time > cutoff_time:
                            stats["change_reports"]["recent_reports"] += 1
                    except Exception:
                        pass
        except Exception:
            stats["change_reports"] = {"total_reports": 0, "recent_reports": 0}

        # Auto-tag cache stats
        try:
            cache_ref = db.collection("auto_tag_cache")
            cache_docs = list(cache_ref.stream())
            stats["auto_tag_cache"] = {"cached_entries": len(cache_docs)}
        except Exception:
            stats["auto_tag_cache"] = {"cached_entries": 0}

        return stats

    except Exception as e:
        logger.error(f"Failed to get Firestore stats: {e}")
        return {}


def get_current_file_content(github_token: str) -> Optional[Dict[str, Any]]:
    """
    Get current content of task_report.md from GitHub.

    Args:
        github_token: GitHub personal access token

    Returns:
        Dictionary with file content and SHA, or None if not found
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{TASK_REPORT_PATH}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return {"content": content, "sha": data["sha"]}
        elif response.status_code == 404:
            logger.info("task_report.md not found, will create new file")
            return None
        else:
            logger.error(f"Failed to get file content: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Failed to get current file content: {e}")
        return None


def generate_task_report_content(stats: Dict[str, Any], ci_stats: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate updated task report content.

    Args:
        stats: Firestore statistics
        ci_stats: CI/CD statistics from GitHub API

    Returns:
        Updated task report markdown content
    """
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    content = f"""# Agent Data Task Report

**Last Updated:** {current_time}
**Generated by:** write_task_report_function (Cloud Function)
**CLI 135:** Automated CI/CD Logging Implementation

## System Overview

The Agent Data system provides document vectorization, metadata management, and intelligent search capabilities using Qdrant vector database and Firestore for metadata storage.

## CI/CD Pipeline Status (CLI 135)

### Nightly Test Suite Performance
- **Total Nightly Runs:** {ci_stats.get('nightly_ci', {}).get('total_nightly_runs', 0) if ci_stats else 0}
- **Average Duration:** {ci_stats.get('nightly_ci', {}).get('avg_duration_minutes', 0) if ci_stats else 0} minutes
- **Under 5 Minutes:** {'✅ Yes' if ci_stats and ci_stats.get('nightly_ci', {}).get('under_5_minutes') else '❌ No'}
- **Last Status:** {ci_stats.get('nightly_ci', {}).get('last_nightly_status', 'unknown').upper() if ci_stats else 'UNKNOWN'}

### Recent CI Runs (Last 8)
{_format_ci_runs_table(ci_stats.get('recent_runs', []) if ci_stats else [])}

## Current Statistics

### Document Management
- **Total Documents:** {stats.get('document_metadata', {}).get('total_documents', 0)}
- **Vectorized Documents:** {stats.get('document_metadata', {}).get('vectorized_documents', 0)}
- **Pending Vectorization:** {stats.get('document_metadata', {}).get('pending_documents', 0)}
- **Failed Vectorization:** {stats.get('document_metadata', {}).get('failed_documents', 0)}
- **Auto-tagged Documents:** {stats.get('document_metadata', {}).get('auto_tagged_documents', 0)}

### Change Tracking
- **Total Change Reports:** {stats.get('change_reports', {}).get('total_reports', 0)}
- **Recent Reports (24h):** {stats.get('change_reports', {}).get('recent_reports', 0)}

### Auto-tagging Cache
- **Cached Tag Entries:** {stats.get('auto_tag_cache', {}).get('cached_entries', 0)}

## Recent Achievements (CLI 119D9)

### ✅ Metadata Versioning and Hierarchy
- Implemented incremental versioning in FirestoreMetadataManager
- Added hierarchical structure with level_1 through level_6 fields
- Version history tracking (last 10 versions)
- Automatic change detection and logging

### ✅ Auto-tagging with OpenAI Integration
- Created AutoTaggingTool with GPT-3.5-turbo integration
- Intelligent tag generation based on document content
- Firestore caching to reduce API calls (24-hour TTL)
- Enhanced metadata with auto-generated tags
- Integration with QdrantVectorizationTool

### ✅ Automated Change Reporting
- Deployed change_report_function Cloud Function
- Firestore trigger-based change detection
- JSON report generation for all document changes
- Configurable storage (Firestore/GCS/both)
- Change analysis and significance detection

### ✅ Task Report Automation
- Automated task_report.md updates via GitHub API
- Real-time statistics from Firestore collections
- Cloud Function deployment for scheduled updates
- Integration with Secret Manager for GitHub token

## System Health

### Vectorization Pipeline
- **Success Rate:** {(stats.get('document_metadata', {}).get('vectorized_documents', 0) / max(stats.get('document_metadata', {}).get('total_documents', 1), 1) * 100):.1f}%
- **Auto-tagging Coverage:** {(stats.get('document_metadata', {}).get('auto_tagged_documents', 0) / max(stats.get('document_metadata', {}).get('total_documents', 1), 1) * 100):.1f}%

### Change Monitoring
- **Change Tracking:** {'Active' if stats.get('change_reports', {}).get('recent_reports', 0) > 0 else 'Inactive'}
- **Report Generation:** {'Functional' if stats.get('change_reports', {}).get('total_reports', 0) > 0 else 'Not Started'}

## Infrastructure Status

### Google Cloud Components
- **Project:** chatgpt-db-project
- **Firestore:** asia-southeast1 (Active)
- **Qdrant Cloud:** us-east4-0 (Active)
- **Cloud Functions:** Deployed
- **Secret Manager:** Configured

### Collections
- `document_metadata`: Primary document metadata storage
- `change_reports`: Automated change tracking
- `auto_tag_cache`: OpenAI tag caching
- `agent_sessions`: User session management

## Next Steps

1. **Deploy Alert Policy:** Monitor Qdrant metrics and latency
2. **Deploy Firestore Rules:** Secure document access
3. **Test Suite Enhancement:** Add metadata versioning tests
4. **Performance Optimization:** Monitor auto-tagging API usage
5. **Documentation Updates:** Complete CLI 119D9 documentation

## Technical Notes

- **Metadata Versioning:** Automatic version increments with change tracking
- **Auto-tagging:** GPT-3.5-turbo with 24-hour cache TTL
- **Change Reports:** Real-time Firestore triggers
- **Task Reports:** Automated GitHub updates via API

---

*This report is automatically generated and updated by the Agent Data system.*
"""

    return content


def update_github_file(github_token: str, content: str, current_file: Optional[Dict[str, Any]]) -> bool:
    """
    Update task_report.md file on GitHub.

    Args:
        github_token: GitHub personal access token
        content: New file content
        current_file: Current file data (content and SHA) or None for new file

    Returns:
        Success status
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{TASK_REPORT_PATH}"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Prepare request data
        data = {
            "message": f"Automated task report update - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "content": encoded_content,
            "branch": "cli103a",  # Update with correct branch
        }

        # Add SHA if updating existing file
        if current_file:
            data["sha"] = current_file["sha"]

        response = requests.put(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            logger.info(f"Successfully updated {TASK_REPORT_PATH}")
            return True
        else:
            logger.error(f"Failed to update file: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to update GitHub file: {e}")
        return False


@functions_framework.http
def write_task_report_handler(request) -> tuple:
    """
    Main Cloud Function handler for task report updates.
    Enhanced with CI/CD logging for CLI 135.

    Args:
        request: HTTP request object

    Returns:
        Tuple of (response_text, status_code)
    """
    try:
        logger.info("Starting task report update with CI/CD logging (CLI 135)")

        # Get GitHub token
        github_token = get_github_token()

        # Get Firestore statistics
        stats = get_firestore_stats()

        # Get CI/CD run data (CLI 135 enhancement)
        ci_runs = get_github_ci_runs(github_token, limit=8)
        nightly_ci_stats = get_nightly_ci_stats(ci_runs)

        ci_stats = {"recent_runs": ci_runs, "nightly_ci": nightly_ci_stats, "total_runs_fetched": len(ci_runs)}

        # Get current file content
        current_file = get_current_file_content(github_token)

        # Generate new content with CI data
        new_content = generate_task_report_content(stats, ci_stats)

        # Update file on GitHub
        success = update_github_file(github_token, new_content, current_file)

        if success:
            response = {
                "status": "success",
                "message": "Task report updated successfully with CI/CD data",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats,
                "ci_stats": ci_stats,
                "cli_135": "automated_logging_active",
            }
            return json.dumps(response), 200
        else:
            response = {
                "status": "failed",
                "message": "Failed to update task report",
                "timestamp": datetime.utcnow().isoformat(),
            }
            return json.dumps(response), 500

    except Exception as e:
        logger.error(f"Error in write_task_report_handler: {e}", exc_info=True)
        response = {"status": "error", "message": str(e), "timestamp": datetime.utcnow().isoformat()}
        return json.dumps(response), 500


# For local testing
if __name__ == "__main__":
    print("Testing task report function...")

    # Mock request for testing
    class MockRequest:
        def __init__(self):
            self.method = "GET"

    response, status = write_task_report_handler(MockRequest())
    print(f"Status: {status}")
    print(f"Response: {response}")
