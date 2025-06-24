#!/bin/bash

# CI Polling Script for fix/fixtures-restore-519 branch
# Compatible with macOS (no timeout command dependency)

set -e

BRANCH="fix/fixtures-restore-519"
MAX_POLLS=100  # 100 polls * 15s = 25 minutes max
POLL_INTERVAL=15
REPO_OWNER="Huyen1974"
REPO_NAME="agent-data"

echo "🔍 Polling CI status for branch: $BRANCH"
echo "📊 Max polling time: $(($MAX_POLLS * $POLL_INTERVAL / 60)) minutes"
echo "⏱️  Poll interval: ${POLL_INTERVAL}s"
echo ""

# Function to check if gh CLI is available
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        echo "❌ Error: GitHub CLI (gh) is not installed or not in PATH"
        echo "📝 Install it with: brew install gh"
        exit 1
    fi
}

# Function to get latest workflow run for the branch
get_latest_run() {
    gh api repos/$REPO_OWNER/$REPO_NAME/actions/runs \
        --jq ".workflow_runs[] | select(.head_branch == \"$BRANCH\") | select(.event == \"push\" or .event == \"pull_request\") | .id, .status, .conclusion, .html_url" \
        | head -4 2>/dev/null || echo "none"
}

# Function to get failing tests from workflow run
get_failing_tests() {
    local run_id=$1
    echo "🔍 Fetching failing tests for run ID: $run_id"
    
    # Get job logs and extract failing test names
    gh api repos/$REPO_OWNER/$REPO_NAME/actions/runs/$run_id/jobs \
        --jq '.jobs[].id' | while read job_id; do
            echo "  📋 Checking job: $job_id"
            gh api repos/$REPO_OWNER/$REPO_NAME/actions/jobs/$job_id/logs 2>/dev/null | \
                grep -E "(FAILED|ERROR)" | \
                grep -oE "tests/[^:]+::[^[:space:]]+" | \
                head -20
        done 2>/dev/null || echo "  ⚠️  Could not fetch detailed failure logs"
}

# Function to parse and display run info
display_run_status() {
    local output="$1"
    
    if [ "$output" = "none" ]; then
        echo "❌ No workflow runs found for branch: $BRANCH"
        echo "🔄 Make sure you've pushed the branch and triggered CI"
        return 1
    fi
    
    # Parse the 4 lines of output
    local run_id=$(echo "$output" | sed -n '1p')
    local status=$(echo "$output" | sed -n '2p')
    local conclusion=$(echo "$output" | sed -n '3p')
    local html_url=$(echo "$output" | sed -n '4p')
    
    echo "🆔 Run ID: $run_id"
    echo "📊 Status: $status"
    echo "🎯 Conclusion: $conclusion"
    echo "🔗 URL: $html_url"
    
    case "$status" in
        "completed")
            if [ "$conclusion" = "success" ]; then
                echo ""
                echo "✅ CI PASSED! Branch is ready for merge."
                echo ""
                echo "🎉 Next steps:"
                echo "   git checkout main"
                echo "   git merge $BRANCH"
                echo "   git tag v0.2-ci-full-pass-$(date +%Y%m%d)"
                echo "   git push origin main --tags"
                return 0
            else
                echo ""
                echo "❌ CI FAILED with conclusion: $conclusion"
                echo ""
                echo "📋 First 20 failing tests:"
                get_failing_tests $run_id
                return 1
            fi
            ;;
        "in_progress"|"queued")
            echo "⏳ CI is running..."
            return 2  # Continue polling
            ;;
        *)
            echo "⚠️  Unknown status: $status"
            return 2
            ;;
    esac
}

# Main polling loop
main() {
    check_gh_cli
    
    local poll_count=0
    
    while [ $poll_count -lt $MAX_POLLS ]; do
        poll_count=$((poll_count + 1))
        
        echo "📊 Poll $poll_count/$MAX_POLLS at $(date '+%H:%M:%S')"
        
        local run_info=$(get_latest_run)
        display_run_status "$run_info"
        local result=$?
        
        case $result in
            0)  # Success
                exit 0
                ;;
            1)  # Failure
                exit 1
                ;;
            2)  # Continue polling
                if [ $poll_count -lt $MAX_POLLS ]; then
                    echo "🕐 Waiting ${POLL_INTERVAL}s before next poll..."
                    sleep $POLL_INTERVAL
                fi
                ;;
        esac
        
        echo ""
    done
    
    echo "⏰ Polling timeout reached ($(($MAX_POLLS * $POLL_INTERVAL / 60)) minutes)"
    echo "🔗 Check manually: https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    exit 1
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 