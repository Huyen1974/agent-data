#!/usr/bin/env python3
"""
CLI140h.2: Google Cloud Build Cleanup Script
Removes old Docker images, Cloud Run revisions, and build artifacts to improve performance.
"""

import subprocess
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_gcloud_command(cmd: List[str]) -> Dict[str, Any]:
    """Run a gcloud command and return parsed JSON output."""
    try:
        cmd_str = ' '.join(cmd)
        logger.info(f"Running: {cmd_str}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            try:
                return {"success": True, "data": json.loads(result.stdout)}
            except json.JSONDecodeError:
                return {"success": True, "data": result.stdout.strip()}
        else:
            return {"success": True, "data": None}
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Stderr: {e.stderr}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"success": False, "error": str(e)}

def cleanup_old_container_images(project_id: str, repository: str = "gcr.io", keep_latest: int = 5) -> bool:
    """Clean up old container images from Google Container Registry."""
    logger.info(f"🧹 Cleaning up old container images in {repository}/{project_id}")
    
    # List all images
    cmd = [
        "gcloud", "container", "images", "list", 
        f"--repository={repository}/{project_id}",
        "--format=json"
    ]
    
    result = run_gcloud_command(cmd)
    if not result["success"]:
        logger.error("Failed to list container images")
        return False
    
    images = result["data"] or []
    logger.info(f"Found {len(images)} container images")
    
    cleanup_count = 0
    for image in images:
        image_name = image.get("name", "")
        if not image_name:
            continue
            
        logger.info(f"Cleaning up old versions of {image_name}")
        
        # List image tags/digests
        list_cmd = [
            "gcloud", "container", "images", "list-tags", 
            image_name,
            "--sort-by=~timestamp",
            f"--limit={keep_latest + 20}",  # Get more to identify old ones
            "--format=json"
        ]
        
        tag_result = run_gcloud_command(list_cmd)
        if not tag_result["success"]:
            continue
            
        tags = tag_result["data"] or []
        if len(tags) <= keep_latest:
            logger.info(f"  Only {len(tags)} versions found, keeping all")
            continue
            
        # Delete old versions (keep the latest ones)
        old_tags = tags[keep_latest:]
        logger.info(f"  Deleting {len(old_tags)} old versions")
        
        for tag in old_tags:
            digest = tag.get("digest")
            if digest:
                delete_cmd = [
                    "gcloud", "container", "images", "delete",
                    f"{image_name}@{digest}",
                    "--quiet"
                ]
                
                delete_result = run_gcloud_command(delete_cmd)
                if delete_result["success"]:
                    cleanup_count += 1
                    logger.info(f"    ✅ Deleted {digest[:12]}...")
                else:
                    logger.warning(f"    ❌ Failed to delete {digest[:12]}...")
    
    logger.info(f"🎯 Container cleanup completed: {cleanup_count} images deleted")
    return True

def cleanup_cloud_run_revisions(service_name: str, region: str = "us-central1", keep_latest: int = 3) -> bool:
    """Clean up old Cloud Run revisions."""
    logger.info(f"🧹 Cleaning up old Cloud Run revisions for {service_name} in {region}")
    
    # List revisions
    cmd = [
        "gcloud", "run", "revisions", "list",
        f"--service={service_name}",
        f"--region={region}",
        "--sort-by=~creationTimestamp",
        "--format=json"
    ]
    
    result = run_gcloud_command(cmd)
    if not result["success"]:
        logger.error("Failed to list Cloud Run revisions")
        return False
    
    revisions = result["data"] or []
    logger.info(f"Found {len(revisions)} revisions")
    
    if len(revisions) <= keep_latest:
        logger.info(f"Only {len(revisions)} revisions found, keeping all")
        return True
    
    # Keep latest revisions, delete old ones
    old_revisions = revisions[keep_latest:]
    cleanup_count = 0
    
    for revision in old_revisions:
        revision_name = revision.get("metadata", {}).get("name", "")
        if not revision_name:
            continue
            
        delete_cmd = [
            "gcloud", "run", "revisions", "delete",
            revision_name,
            f"--region={region}",
            "--quiet"
        ]
        
        delete_result = run_gcloud_command(delete_cmd)
        if delete_result["success"]:
            cleanup_count += 1
            logger.info(f"  ✅ Deleted revision {revision_name}")
        else:
            logger.warning(f"  ❌ Failed to delete revision {revision_name}")
    
    logger.info(f"🎯 Cloud Run cleanup completed: {cleanup_count} revisions deleted")
    return True

def cleanup_cloud_build_history(days_to_keep: int = 30) -> bool:
    """Clean up old Cloud Build history."""
    logger.info(f"🧹 Cleaning up Cloud Build history older than {days_to_keep} days")
    
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    # List builds
    cmd = [
        "gcloud", "builds", "list",
        "--sort-by=~createTime",
        "--filter=f'createTime < {cutoff_str}'",
        "--format=json",
        "--limit=100"  # Safety limit
    ]
    
    result = run_gcloud_command(cmd)
    if not result["success"]:
        logger.warning("Failed to list Cloud Build history (may not have builds)")
        return True
    
    builds = result["data"] or []
    logger.info(f"Found {len(builds)} old builds to potentially clean")
    
    # Note: gcloud doesn't have a direct delete command for builds
    # Build history is automatically cleaned up by Google Cloud after 120 days
    # We'll just log what we found
    for build in builds[:10]:  # Show first 10
        build_id = build.get("id", "unknown")
        create_time = build.get("createTime", "unknown")
        logger.info(f"  Old build: {build_id} created at {create_time}")
    
    logger.info("ℹ️  Cloud Build history is automatically cleaned by Google after 120 days")
    return True

def get_project_info() -> Dict[str, str]:
    """Get current Google Cloud project information."""
    project_cmd = ["gcloud", "config", "get-value", "project"]
    result = run_gcloud_command(project_cmd)
    
    if result["success"] and result["data"]:
        project_id = result["data"].strip()
        logger.info(f"📋 Current project: {project_id}")
        return {"project_id": project_id}
    else:
        logger.error("❌ Failed to get project ID")
        return {}

def main():
    """Main cleanup function."""
    logger.info("🚀 Starting CLI140h.2 Google Cloud cleanup...")
    
    # Get project info
    project_info = get_project_info()
    if not project_info:
        logger.error("Cannot proceed without project information")
        sys.exit(1)
    
    project_id = project_info["project_id"]
    
    # Run cleanup operations
    success_count = 0
    
    # 1. Clean up container images
    if cleanup_old_container_images(project_id):
        success_count += 1
    
    # 2. Clean up Cloud Run revisions (common service names)
    common_services = ["agent-data", "qdrant-agent", "mcp-gateway"]
    for service in common_services:
        try:
            if cleanup_cloud_run_revisions(service):
                success_count += 1
        except Exception as e:
            logger.warning(f"Service {service} may not exist: {e}")
    
    # 3. Check Cloud Build history
    if cleanup_cloud_build_history():
        success_count += 1
    
    # Summary
    logger.info(f"🎯 Cleanup completed: {success_count} operations successful")
    logger.info("✅ Google Cloud cleanup finished!")
    
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 