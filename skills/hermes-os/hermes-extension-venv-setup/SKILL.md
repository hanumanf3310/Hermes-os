---
name: hermes-extension-venv-setup
description: |
  Set up isolated Python virtual environments for Hermes OS extensions and components.
  Creates properly configured venvs, installs dependencies via RTK-MES policy, and verifies
  installation. Used when core Hermes venv has limitations or new components need isolation.

  Trigger: Need to install Python packages outside core Hermes venv, venv conflicts,
  component isolation requirements, or dependency version conflicts.

  Pattern: Create venv at ~/.hermes/<component>-venv/ → Install deps via rtk run →
  Verify imports → Document for Hermes integration.
category: hermes-os
tags: [hermes-os, venv, python, isolation, dependency-management, rtk-mes, infrastructure]
version: 1.0.0
---

# Hermes Extension Venv Setup

## Purpose

Create isolated Python virtual environments for Hermes OS extensions when:
- Core Hermes venv lacks pip/isolated from system
- New component needs different Python version
- Dependency conflicts with core Hermes packages
- Required for security/isolation (untrusted packages)
- Component is experimental and needs rollback capability

## Pattern

```
~/.hermes/
├── hermes-agent/venv/          # Core Hermes (hands-off)
├── <component>-venv/           # New isolated venv
│   ├── bin/python
│   ├── bin/pip
│   └── lib/python3.x/
└── <component>/               # Component code
```

## Workflow

### 1. Create Venv (RTK-MES)

```bash
rtk run "python3 -m venv ~/.hermes/<component>-venv --system-site-packages"
```

Options:
- `--system-site-packages`: Allow access to system packages (faster install)
- Omit for pure isolation (more secure)

### 2. Verify Venv

```bash
rtk run "ls -la ~/.hermes/<component>-venv/bin/ | grep -E 'python|pip'"
rtk run "~/.hermes/<component>-venv/bin/python --version"
rtk run "~/.hermes/<component>-venv/bin/pip --version"
```

### 3. Install Dependencies (RTK-MES)

```bash
# Single package
rtk run "~/.hermes/<component>-venv/bin/pip install -q <package>"

# Multiple packages
rtk run "~/.hermes/<component>-venv/bin/pip install -q <pkg1> <pkg2> <pkg3>"

# With specific versions
rtk run "~/.hermes/<component>-venv/bin/pip install <package>==<version>"
```

### 4. Verify Installation

```bash
rtk run "~/.hermes/<component>-venv/bin/python -c 'import <module>; print(\"OK\")'"
```

### 5. Document

Create activation wrapper or PATH note:
```bash
# ~/.hermes/<component>/bin/activate-venv
source ~/.hermes/<component>-venv/bin/activate
exec "$@"
```

## Common Patterns

### RAG Tools Venv
```bash
rtk run "python3 -m venv ~/.hermes/rag-venv"
rtk run "~/.hermes/rag-venv/bin/pip install -q lancedb sentence-transformers"
rtk run "~/.hermes/rag-venv/bin/python -c 'import lancedb; print(lancedb.__version__)'"
```

### ML/AI Tools Venv (GPU)
```bash
rtk run "python3 -m venv ~/.hermes/ml-venv"
rtk run "~/.hermes/ml-venv/bin/pip install torch torchvision transformers"
```

### Legacy Python 3.10 Venv
```bash
rtk run "python3.10 -m venv ~/.hermes/legacy-venv"
```

## Troubleshooting

### No pip in venv
```bash
rtk run "python3 -m ensurepip --upgrade"
```

### Permission denied
```bash
rtk run "chmod +x ~/.hermes/<component>-venv/bin/*"
```

### Import errors after install
```bash
# Check venv site-packages
rtk run "~/.hermes/<component>-venv/bin/python -c 'import site; print(site.getsitepackages())'"

# Reinstall with verbose
rtk run "~/.hermes/<component>-venv/bin/pip install -v <package>"
```

## Integration with Hermes

### Option 1: Direct Python Path
```python
# In Hermes skill/tool
import subprocess
result = subprocess.run(
    ["~/.hermes/rag-venv/bin/python", "script.py"],
    capture_output=True
)
```

### Option 2: Wrapper Script
```bash
# ~/.hermes/bin/rag-python
#!/bin/bash
exec ~/.hermes/rag-venv/bin/python "$@"
```

### Option 3: Hermes Config
```yaml
# ~/.hermes/config.yaml
venvs:
  rag:
    python: ~/.hermes/rag-venv/bin/python
    pip: ~/.hermes/rag-venv/bin/pip
```

## Policy Compliance

- ✅ Always use `rtk run` for terminal commands (RTK-MES policy)
- ✅ Create venv under `~/.hermes/` (not scattered)
- ✅ Verify installation before claiming success
- ✅ Document venv purpose and contents
- ✅ Consider `--system-site-packages` for performance vs isolation trade-off

## Examples

See linked templates:
- `templates/create-rag-venv.sh` — Full RAG setup
- `templates/create-ml-venv.sh` — PyTorch/ML setup
- `templates/verify-venv.py` — Verification script

## Related Skills

- `hermes-desktop-launcher` — Desktop app isolation (similar pattern)
- `hermes-os-integration` — Component integration (uses venvs)
- `rtk-mes` — Required for all terminal commands
