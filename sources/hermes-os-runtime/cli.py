#!/usr/bin/env python3
"""
Hermes OS CLI Integration

This module integrates Hermes OS with the hermes-os command.
When running in Hermes OS mode, all tasks flow through the unified
Hermes OS layer with automatic Fleet routing.

Usage:
    hermes-os                    # Enter Hermes OS mode
    hermes-os status             # Show status
    hermes-os execute "task"     # Execute task
    hermes-os shutdown           # Shutdown OS mode
"""

import json
import os
import sys
from pathlib import Path

# Add Hermes OS to path
HERMES_OS_DIR = Path.home() / ".hermes" / "os"
sys.path.insert(0, str(HERMES_OS_DIR))

def load_hermes_os():
    """Load Hermes OS core."""
    try:
        from hermes_os import HermesOS, get_os
        return get_os()
    except ImportError as e:
        print(f"Error loading Hermes OS: {e}")
        print(f"Make sure {HERMES_OS_DIR}/hermes_os.py exists")
        sys.exit(1)

def cmd_status():
    """Show Hermes OS status."""
    os = load_hermes_os()
    status = os.status()

    from core.response_formatter import format_os_status
    print(format_os_status(status))

def cmd_execute(task_description: str):
    """Execute a task through Hermes OS."""
    os = load_hermes_os()

    print(f"🛰️ Hermes OS")
    print(f"━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"Task: {task_description}")
    print()
    print("Analyzing...")

    result = os.execute(task_description)

    print()
    print("Result:")
    print(json.dumps(result, indent=2, default=str))

def cmd_shutdown():
    """Shutdown Hermes OS."""
    os = load_hermes_os()
    os.shutdown()
    print("🛑 Hermes OS shutdown complete")

def cmd_fleet_status():
    """Show Fleet status."""
    os = load_hermes_os()

    if not os.fleet:
        print("❌ Fleet not available")
        return

    from core.response_formatter import format_status
    health = os.fleet.health()
    print(format_status(health))

def cmd_route(task_description: str):
    """Routing has been removed from Hermes OS."""
    print("❌ Hermes OS direct mode only. Use explicit Hermes/Fleet commands instead.")

def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        # Default: show status
        cmd_status()
        return

    command = sys.argv[1]

    if command == "status":
        cmd_status()

    elif command == "execute" and len(sys.argv) > 2:
        task = " ".join(sys.argv[2:])
        cmd_execute(task)

    elif command == "shutdown":
        cmd_shutdown()

    elif command == "fleet" and len(sys.argv) > 2:
        subcmd = sys.argv[2]
        if subcmd == "status":
            cmd_fleet_status()
        else:
            print(f"Unknown fleet command: {subcmd}")

    elif command == "route" and len(sys.argv) > 2:
        task = " ".join(sys.argv[2:])
        cmd_route(task)

    else:
        print("Usage: hermes-os [command]")
        print()
        print("Commands:")
        print("  status                     Show Hermes OS status")
        print("  execute \"task\"            Execute a task")
        print("  fleet status               Show Fleet status")
        print("  shutdown                   Shutdown Hermes OS")
        print()
        print("Examples:")
        print('  hermes-os execute "Build Python API"')
        print('  hermes-os fleet status')

if __name__ == "__main__":
    main()
