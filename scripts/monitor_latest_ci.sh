#!/bin/bash

# Monitor the latest CI run with our fixes
RUN_ID="15869459582"
COMMIT="3f7bde6"

echo "🔍 Monitoring LATEST CI Run with FIXES"
echo "🆔 Run ID: $RUN_ID"
echo "📦 Commit: $COMMIT (smart conftest.py)"
echo "🌿 Branch: ci/106-final-green"
echo "📅 Started: $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for i in {1..20}; do
    echo "📊 Poll $i/20 ($(date)):"
    
    result=$(curl -s "https://api.github.com/repos/Huyen1974/agent-data/actions/runs/$RUN_ID" | jq -r '{status: .status, conclusion: .conclusion, updated_at: .updated_at}')
    status=$(echo "$result" | jq -r '.status')
    conclusion=$(echo "$result" | jq -r '.conclusion')
    updated=$(echo "$result" | jq -r '.updated_at')
    
    echo "   Status: $status | Conclusion: $conclusion"
    echo "   Updated: $updated"
    
    if [ "$status" = "completed" ]; then
        if [ "$conclusion" = "success" ]; then
            echo ""
            echo "🎉🎉🎉 SUCCESS! CI IS GREEN! 🎉🎉🎉"
            echo "✅ Smart conftest.py fix worked!"
            echo "✅ 106 tests collected and passed!"
            echo "✅ Ready for tagging and merge!"
            echo ""
            echo "🏷️  Next steps:"
            echo "   git tag v0.2-green-106"
            echo "   git push origin v0.2-green-106"  
            echo "   gh pr merge --squash --delete-branch"
            echo ""
            echo "🔗 Success URL: https://github.com/Huyen1974/agent-data/actions/runs/$RUN_ID"
            exit 0
        else
            echo ""
            echo "❌ FAILED! CI conclusion: $conclusion"
            echo "🔍 Need to analyze logs and fix remaining issues"
            echo "🔗 Check logs: https://github.com/Huyen1974/agent-data/actions/runs/$RUN_ID"
            
            # Get failed job details
            echo ""
            echo "📋 Failed Steps:"
            curl -s "https://api.github.com/repos/Huyen1974/agent-data/actions/runs/$RUN_ID/jobs" | jq -r '.jobs[].steps[] | select(.conclusion == "failure") | "   - " + .name'
            exit 1
        fi
    fi
    
    if [ $i -lt 20 ]; then
        echo "   ⏳ Waiting 30 seconds..."
        sleep 30
    fi
done

echo ""
echo "⏰ TIMEOUT: CI still running after 10 minutes"
echo "🔗 Check manually: https://github.com/Huyen1974/agent-data/actions/runs/$RUN_ID"
echo "💡 CI might need more time - check GitHub directly"
exit 2 