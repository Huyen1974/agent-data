# 🌍 GLOBAL RULES (Simplified)

## 1. Single Project Only
You are working **exclusively** on one project:
/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid

Do not interact with any other project, repo, or directory.
Do not read, write, or reference unrelated projects.

🚫 Forbidden paths:
- */Manual Deploy/Archive_ADK/agent-data-legacy
- any folder matching /ADK.*/

---

## 2. Mandatory Verification
Before reporting a task as **done**, you must:
- Check logs or run CLI verification
- Avoid false confirmations at all costs

---

## 3. Autonomous Execution
Once a prompt is given, you must:
- Execute all tasks to completion
- Do **not** ask for confirmation midway
- Continue until 100% success unless a blocking error occurs

---

## Self-check before git push

Note: If .git/hooks/pre-push is missing, recreate with the following content:
```bash
#!/usr/bin/env bash
set -e
remote=$(git remote get-url origin)
pwd_current=$(pwd)

[[ "$remote" == *"agent-data-test"* ]] || { echo "❌ Wrong remote: $remote"; exit 1; }
pwd | grep -q "/agent-data-langroid$" || { echo "❌ Wrong folder: $pwd_current"; exit 1; }
echo "✅ Pre-push self-check passed"
```

Before any git push, you must run and pass the following commands:
1. Check the Git remote URL:
   Command: git remote get-url origin
   Expected: The URL must contain "agent-data-test"
2. Check current working directory:
   Command: pwd | grep -q "/Manual Deploy/agent-data-langroid$"
# CI check (optional)
if gh run list -L1 >/dev/null 2>&1; then
    echo "ℹ️ CI run detected (green or red). Push fixes freely, but MERGE only when green."
fi 