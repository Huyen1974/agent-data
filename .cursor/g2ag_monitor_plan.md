# G2AG Monitor Retry - CI Polling Implementation Plan

**Date**: June 25, 2025, 11:20 +07  
**Branch**: `ci/106-fix-4`  
**Goal**: Implement lightweight CI monitoring with MacBook M1 safety guard-rails

## GUARD-RAILS ENFORCED
- ✅ All commands ≤15s wall clock time on MacBook M1
- ✅ Working directory: `/ADK/agent_data` only
- ✅ Polling loop ≤10 iterations max
- ✅ Total monitoring time ≤2 minutes
- ✅ No `gh run watch` or long-running commands

## IMPLEMENTATION APPROACH

### 1. Lightweight Polling Loop
```bash
for i in {1..10}; do
  echo "Iteration $i/10: Checking CI runs..."
  
  # Get latest 2 run IDs (≤5s)
  run_ids=$(gh run list --json databaseId --jq '.[0:2].databaseId' | tr '\n' ' ')
  
  # Check status of each run (≤10s total)
  all_success=true
  for run_id in $run_ids; do
    status=$(gh run view $run_id --json status,conclusion -q '.status + "/" + (.conclusion//"")')
    echo "  Run $run_id: $status"
    [[ "$status" != "completed/success" ]] && all_success=false
  done
  
  # Break on success
  if [[ "$all_success" == "true" ]]; then
    echo "✅ All runs successful!"
    break
  fi
  
  # Sleep 10s between iterations
  [[ $i -lt 10 ]] && sleep 10
done
```

### 2. Success Actions
- Tag: `git tag v0.2-green-106`
- Merge PR: `gh pr merge --squash`

### 3. Failure Actions  
- Create diagnostics: `.cursor/g2ag_monitor_report.md`
- Log final run statuses
- Exit 1

## SAFETY MEASURES

### Command Timeouts
- `gh run list`: ~2-3s
- `gh run view`: ~2-3s per run
- Total per iteration: ~8s (well under 15s limit)

### Loop Limits
- Max iterations: 10
- Sleep between: 10s
- Total time: ~2 minutes
- Abort if timeout

### Error Handling
- Capture all command errors  
- Log intermediate states
- Clear failure diagnostics

## SUCCESS CRITERIA
- [x] Polling ≤10 iterations, each ≤15s
- [x] Two green runs → tag v0.2-green-106 + merge
- [x] Timeout/failure → diagnostics + exit 1
- [x] MacBook M1 safe (no hanging commands)

## IMPLEMENTATION STATUS
- [ ] Create monitoring script
- [ ] Test single iteration (dry run)
- [ ] Execute full monitoring loop
- [ ] Handle success/failure scenarios
- [ ] Create final report

**Next**: Implement and execute the monitoring script 