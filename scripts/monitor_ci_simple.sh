#!/bin/bash

# Monitor CI run 15868964566
RUN_ID="15868964566"
BRANCH="ci/106-final-green"

echo "🔍 Monitoring CI Run: $RUN_ID"
echo "📅 Started: $(date)"
echo "🌿 Branch: $BRANCH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for i in {1..20}; do
    echo "📊 Poll $i/20:"
    
    status=$(curl -s "https://api.github.com/repos/Huyen1974/agent-data/actions/runs/$RUN_ID" | jq -r '.status // "unknown"')
    conclusion=$(curl -s "https://api.github.com/repos/Huyen1974/agent-data/actions/runs/$RUN_ID" | jq -r '.conclusion // "null"')
    
    echo "   Status: $status | Conclusion: $conclusion"
    
    if [ "$status" = "completed" ]; then
        if [ "$conclusion" = "success" ]; then
            echo "🎉 SUCCESS! CI is GREEN ✅"
            echo "🏷️  Ready to tag v0.2-green-106"
            echo "🔀 Ready to merge PR #13"
            exit 0
        else
            echo "❌ FAILED! CI conclusion: $conclusion"
            echo "🔍 Check logs: https://github.com/Huyen1974/agent-data/actions/runs/$RUN_ID"
            exit 1
        fi
    fi
    
    if [ $i -lt 20 ]; then
        echo "   ⏳ Waiting 30 seconds..."
        sleep 30
    fi
done

echo "⏰ Timeout: CI still running after 10 minutes"
echo "🔗 Check manually: https://github.com/Huyen1974/agent-data/actions/runs/$RUN_ID"
exit 2 