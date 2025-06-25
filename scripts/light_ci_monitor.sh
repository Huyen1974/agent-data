#!/usr/bin/env bash
ids=( $(gh run list --limit 2 --json databaseId --jq '.[].databaseId') )
for i in {1..5}; do
  status1=$(gh run view "${ids[0]}" --json status,conclusion -q '.status+ "/" +(.conclusion//"")')
  status2=$(gh run view "${ids[1]}" --json status,conclusion -q '.status+ "/" +(.conclusion//"")')
  echo "[$i] $status1 | $status2"
  if [[ $status1 == "completed/success" && $status2 == "completed/success" ]]; then
    gh tag create v0.2-green-106 && gh pr merge --squash 1
    exit 0
  fi
  sleep 5
done
echo "CI never passed: $status1 | $status2" > .cursor/g2ah_monitor_report.md
exit 1
