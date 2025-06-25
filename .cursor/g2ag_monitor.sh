#!/bin/bash
# G2AG Monitor Retry - Lightweight CI Polling Script
# MacBook M1 Safe: All commands ≤15s, max 10 iterations

set -e

echo "🔍 G2AG CI Monitor Starting..."
echo "Branch: $(git branch --show-current)"
echo "Time: $(date)"
echo "Guard-rails: ≤15s per command, ≤10 iterations"
echo "================================================"

# Initialize variables
iteration=0
max_iterations=10
all_success=false
final_report=""

# Main polling loop
for i in {1..10}; do
    iteration=$i
    echo "⏱️  Iteration $i/$max_iterations: Checking CI runs..."
    
    # Get latest 2 run IDs (timeout after 10s)
    echo "   Fetching run IDs..."
    if ! run_ids=$(timeout 10s gh run list --json databaseId --jq '.[0:2].databaseId' 2>/dev/null | tr '\n' ' '); then
        echo "❌ Failed to fetch run IDs (timeout/error)"
        final_report="ERROR: Could not fetch CI run IDs at iteration $i"
        break
    fi
    
    if [[ -z "$run_ids" ]]; then
        echo "❌ No CI runs found"
        final_report="ERROR: No CI runs found at iteration $i"
        break
    fi
    
    echo "   Found runs: $run_ids"
    
    # Check status of each run
    all_success=true
    run_statuses=""
    
    for run_id in $run_ids; do
        echo "   Checking run $run_id..."
        
        # Get run status (timeout after 8s)
        if ! status=$(timeout 8s gh run view $run_id --json status,conclusion -q '.status + "/" + (.conclusion//"")'  2>/dev/null); then
            echo "     ❌ Failed to get status (timeout/error)"
            all_success=false
            run_statuses="$run_statuses\nRun $run_id: ERROR/TIMEOUT"
            continue
        fi
        
        echo "     Status: $status"
        run_statuses="$run_statuses\nRun $run_id: $status"
        
        # Check if this run is successful
        if [[ "$status" != "completed/success" ]]; then
            all_success=false
        fi
    done
    
    # Update final report with current iteration
    final_report="Iteration $i/$max_iterations completed:$run_statuses"
    
    # Break on success
    if [[ "$all_success" == "true" ]]; then
        echo "✅ All runs successful at iteration $i!"
        break
    fi
    
    # Sleep between iterations (except last)
    if [[ $i -lt $max_iterations ]]; then
        echo "   Waiting 10s before next check..."
        sleep 10
    fi
done

echo "================================================"

# Handle results
if [[ "$all_success" == "true" ]]; then
    echo "🎉 SUCCESS: All CI runs completed successfully!"
    echo "Proceeding with tagging and merge..."
    
    # Tag the successful build
    echo "🏷️  Tagging v0.2-green-106..."
    git tag v0.2-green-106
    git push origin v0.2-green-106
    
    # Get current PR number
    pr_number=$(gh pr view --json number -q '.number' 2>/dev/null || echo "")
    
    if [[ -n "$pr_number" ]]; then
        echo "🔀 Merging PR #$pr_number..."
        gh pr merge $pr_number --squash --delete-branch
        echo "✅ PR #$pr_number merged successfully!"
    else
        echo "⚠️  No open PR found, skipping merge"
    fi
    
    # Create success report
    cat > .cursor/g2ag_monitor_report.md << EOF
# G2AG Monitor Success Report

**Date**: $(date)
**Branch**: $(git branch --show-current)
**Status**: ✅ SUCCESS
**Iterations**: $iteration/$max_iterations

## Results
- All CI runs completed successfully
- Tagged: v0.2-green-106
- PR merged: ${pr_number:-"N/A"}

## Final Run Statuses
$run_statuses

## Performance
- Total iterations: $iteration
- Total time: ~$((iteration * 10))s
- MacBook M1 safe: All commands <15s

**Status**: COMPLETE - CI monitoring successful
EOF

    echo "📝 Success report written to .cursor/g2ag_monitor_report.md"
    exit 0
    
else
    echo "❌ FAILURE: CI runs not successful after $iteration iterations"
    echo "Writing diagnostics..."
    
    # Create failure diagnostics
    cat > .cursor/g2ag_monitor_report.md << EOF
# G2AG Monitor Failure Report

**Date**: $(date)
**Branch**: $(git branch --show-current)
**Status**: ❌ FAILURE
**Iterations**: $iteration/$max_iterations

## Problem
CI runs did not reach completed/success status within $max_iterations iterations.

## Final Status
$final_report

## Diagnostics
$run_statuses

## Recommendations
1. Check GitHub Actions logs manually
2. Review CI workflow configuration
3. Retry monitoring or investigate failures

## Performance
- Total iterations: $iteration
- Total time: ~$((iteration * 10))s
- MacBook M1 safe: All commands <15s

**Status**: FAILED - Manual intervention required
EOF

    echo "📝 Failure report written to .cursor/g2ag_monitor_report.md"
    exit 1
fi 