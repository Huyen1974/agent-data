#!/bin/bash
# G2AD CI Monitoring Script (MacBook M1 Safe)

echo "=== G2AD CI MONITORING ==="
echo "Branch: ci/106-fix-flag"
echo "PR: #11"
echo "Started: $(date)"

# Simple API check with 15s timeout safety
check_run() {
    echo "Checking CI status..."
    curl -s -m 10 -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/Huyen1974/agent-data/actions/runs?branch=ci/106-fix-flag&per_page=2" \
      | grep -E "(status|conclusion)" | head -4
}

# Check run status
check_run

echo ""
echo "Manual monitoring commands:"
echo "1. Check status: curl -s 'https://api.github.com/repos/Huyen1974/agent-data/actions/runs?branch=ci/106-fix-flag&per_page=2' | grep status"
echo "2. Visit: https://github.com/Huyen1974/agent-data/actions"
echo "3. PR: https://github.com/Huyen1974/agent-data/pull/11"

echo ""
echo "On success (2 green runs):"
echo "git tag v0.2-green-106 && git push origin v0.2-green-106"
echo "gh pr merge 11 --squash"
echo ""
echo "=== Monitor ready ===" 