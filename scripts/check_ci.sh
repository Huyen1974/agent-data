#!/bin/bash
for i in {1..10}; do
  statuses=$(gh run list --branch ci/106-final-green --limit 2 --json status,conclusion --jq 'map(.status + "/" + (.conclusion // "null")) | join(" ")')
  echo "Poll $i: $statuses"
  if [[ "$statuses" == "completed/success completed/success" ]]; then
    git tag v0.2-green-106
    git push origin v0.2-green-106
    gh pr merge --squash --delete-branch
    echo "CI green – Step 2 finished" > .cursor/g2ai_success.md
    exit 0
  fi
  sleep 5
done
echo "CI failed after 10 polls: $statuses" > .cursor/g2ai_failure.md
exit 1 