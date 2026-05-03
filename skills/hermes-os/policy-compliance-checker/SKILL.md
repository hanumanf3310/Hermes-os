---
name: policy-compliance-checker
version: 1.0.0
description: |
  Automated codebase policy compliance checker for Hermes OS.
  Scans Python files against Hermes OS Policy Gateway rules (RTK-MES, UTC+7, Evidence-first).
  Provides evidence-based reports with line-by-line violations and recommendations.
author: hanuman3310
tags: [hermes-os, policy, compliance, validation, security]
trigger: |
  When needing to:
  - Check new code for Hermes OS Policy compliance
  - Validate existing codebase against Policy Gateway
  - Find UTC+7, RTK-MES, or Evidence-first violations
  - Pre-commit policy validation
  - CI/CD integration for Hermes projects

  Use this skill whenever code files need validation against Hermes OS policy rules
  before deployment or merge.
---

# Policy Compliance Checker Skill

## Purpose

Automatically validate Python code files against Hermes OS Policy Gateway rules:
- **RTK-MES**: All terminal() calls must use `rtk run` wrapper
- **UTC+7**: All datetime.now() must use `ZoneInfo("Asia/Bangkok")`
- **Evidence-first**: Code must include evidence markers (✅, evidence:, ผลลัพธ์:)

## Usage

### Basic Check
```python
from agent.policy_compliance_checker import check_compliance, quick_check

# Full report
result = check_compliance("/path/to/file.py")
print(result['report'])

# Quick summary only
summary = quick_check("/path/to/file.py")
print(summary)
```

### Scan Multiple Files
```python
from agent.policy_compliance_checker import check_compliance
import os

files = [
    "run_agent.py",
    "cli.py",
    "gateway/run.py"
]

violations = 0
for f in files:
    if os.path.exists(f):
        result = check_compliance(f)
        if result['status'] == 'success':
            violations += len(result['violations'])
```

## Policy Rules

### 1. RTK Enforcement
```python
# ❌ Non-compliant
terminal("ls -la")

# ✅ Compliant
rtk run "ls -la"
```

### 2. UTC+7 Normalization
```python
# ❌ Non-compliant
from datetime import datetime
now = datetime.now()

# ✅ Compliant
from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo("Asia/Bangkok"))
```

### 3. Evidence-First Pattern
```python
# ❌ Non-compliant
print("Done")

# ✅ Compliant
print("Done — Evidence: 5 files processed, 0 errors")
```

## Output Format

Reports include:
1. **Status**: success/error
2. **Violations**: Line-by-line findings with rule name
3. **Compliant Patterns**: What's done correctly
4. **Recommendations**: Specific fixes needed

Example report:
```
==================================================
🛡️ Policy Compliance Report
==================================================
File: run_agent.py
Policy: Hermes OS Policy Gateway
--------------------------------------------------

✅ No violations found!

✅ Compliant Patterns:
   • Uses evidence-first pattern
   • Uses Asia/Bangkok timezone normalization

💡 Recommendations:
   → All checks passed! No recommendations needed.

==================================================
```

## File Structure

```
agent/policy_compliance_checker.py     # Core checker
tests/agent/test_policy_compliance_checker.py  # TDD tests
```

## Safety Guarantees

- **READ-ONLY**: Never modifies target files
- **Fail-safe**: Returns empty violations if policy file not found
- **Graceful degradation**: Reports errors without crashing

## Integration

### Pre-commit Hook
```bash
#!/bin/bash
# .pre-commit-policy.sh
python -c "
from agent.policy_compliance_checker import check_compliance
import sys
result = check_compliance(sys.argv[1])
if result['violations']:
    print(result['report'])
    sys.exit(1)
" "$1"
```

### CI/CD Integration
```yaml
# .github/workflows/policy-check.yml
- name: Policy Compliance Check
  run: |
    python -m pytest tests/agent/test_policy_compliance_checker.py -v
```

## Policy File Discovery

Checker searches for policy file at:
1. `~/.hermes/website/docs/reference/merged-hard-gate-policy.yaml`
2. `~/hermes-agent/website/docs/reference/merged-hard-gate-policy.yaml`

Returns error if policy not found.

## Extension

Add new policy rules by extending:
```python
def _check_new_rule(code: str) -> List[str]:
    violations = []
    # Pattern detection logic
    return violations
```

Then add to `check_compliance()`:
```python
new_violations = _check_new_rule(target_content)
if new_violations:
    violations.extend(new_violations)
```

## Testing

Always run tests before deployment:
```bash
python -m pytest tests/agent/test_policy_compliance_checker.py -v
```

Expected: 6 passed tests covering:
- Policy file requirements
- Target file reading
- RTK violation detection
- UTC+7 compliance approval
- Evidence-based reporting
- Read-only guarantees
