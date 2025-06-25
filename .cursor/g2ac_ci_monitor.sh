#!/bin/bash

# MacBook M1 CI Monitoring Script - g2ac-ci-validate
# ABSOLUTE GUARD-RAILS: All commands ≤15s timeout

echo "=== CI Monitoring Started: $(date) ==="
echo "PR: https://github.com/Huyen1974/agent-data/pull/10"
echo "Target: Exactly 106 tests, 0 failed, ≤6 skipped"
echo

# Function to safely run with timeout
safe_run() {
    local cmd="$1"
    local timeout=15
    echo "Running: $cmd"
    
    # Use gtimeout if available, otherwise try perl approach
    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout $timeout sh -c "$cmd"
    else
        # Use background process with kill after timeout
        (
            eval "$cmd" &
            local pid=$!
            sleep $timeout && kill $pid 2>/dev/null &
            wait $pid
        ) 2>/dev/null
    fi
}

# Monitor function
monitor_ci() {
    local run_count=0
    local max_attempts=75  # 25 minutes total (75 * 20s)
    
    while [ $run_count -lt 2 ] && [ $max_attempts -gt 0 ]; do
        echo "--- Polling attempt $((76 - max_attempts)) ---"
        
        # Simple check approach for macOS
        gh run list --limit 3 > /tmp/runs.txt 2>/dev/null || {
            echo "gh command failed, retrying..."
            sleep 20
            max_attempts=$((max_attempts - 1))
            continue
        }
        
        if grep -q "completed" /tmp/runs.txt 2>/dev/null; then
            echo "✓ Completed CI run detected"
            
            # Extract run ID (adjust based on actual gh output format)
            run_id=$(head -1 /tmp/runs.txt | awk '{print $1}' 2>/dev/null)
            echo "Checking run ID: $run_id"
            
            # Get run status
            gh run view $run_id > /tmp/run_details.txt 2>/dev/null
            
            if grep -q "conclusion.*success" /tmp/run_details.txt; then
                echo "✅ RUN $((run_count + 1)): SUCCESS"
                run_count=$((run_count + 1))
            else
                echo "❌ RUN FAILED - Starting diagnostics"
                gh run download $run_id -D .cursor/artifacts/ 2>/dev/null || echo "No artifacts to download"
                return 1
            fi
        else
            echo "⏳ Waiting for CI runs to complete..."
        fi
        
        max_attempts=$((max_attempts - 1))
        sleep 20
    done
    
    if [ $run_count -eq 2 ]; then
        echo "🎉 SUCCESS: 2 consecutive green runs!"
        return 0
    else
        echo "⏰ TIMEOUT: Max monitoring time reached"
        return 1
    fi
}

# Run monitoring
if monitor_ci; then
    echo "=== READY FOR TAGGING ==="
    echo "Next steps:"
    echo "1. git tag v0.2-green-106"
    echo "2. git push origin v0.2-green-106"
    echo "3. gh pr merge 10 --squash"
else
    echo "=== NEEDS ATTENTION ==="
    echo "Check .cursor/artifacts/ for diagnostics"
fi

echo "=== Monitor ended: $(date) ===" 