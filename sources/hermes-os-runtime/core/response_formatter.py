"""
ResponseFormatter - Unified output formatting for Hermes OS.

Formats responses from both Hermes Agent and Enterprise Agent Fleet
into consistent, human-readable output for Boss via Telegram/Discord.
"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Any, Optional, List, Union


class ResponseFormatter:
    """
    Unified response formatter for Hermes OS.

    Converts execution results into:
    - Telegram-friendly markdown
    - Concise summaries for quick tasks
    - Detailed reports for complex tasks
    - Error messages with actionable suggestions
    """

    # Emoji mapping for different statuses
    STATUS_EMOJIS = {
        "completed": "✅",
        "failed": "❌",
        "blocked": "🚫",
        "pending": "⏳",
        "running": "🔄",
        "safety_check": "🛡️",
        "qa_gate": "🔍",
    }

    # Route indicators
    ROUTE_ICONS = {
        "hermes_direct": "⚡",
        "fleet_complex": "🚀",
        "fleet_safety": "🛡️",
        "fleet_multi": "🌐",
    }

    def format(
        self,
        result: Dict[str, Any],
        mode: str = "auto",
        platform: str = "telegram"
    ) -> str:
        """
        Format execution result for output.

        Args:
            result: Execution result dict from Hermes or Fleet
            mode: 'auto', 'summary', 'detailed', or 'minimal'
            platform: 'telegram', 'discord', or 'terminal'

        Returns:
            Formatted string ready for display
        """
        if mode == "auto":
            mode = self._detect_mode(result)

        if mode == "minimal":
            return self._format_minimal(result)
        elif mode == "summary":
            return self._format_summary(result, platform)
        else:  # detailed
            return self._format_detailed(result, platform)

    def _detect_mode(self, result: Dict[str, Any]) -> str:
        """Auto-detect appropriate format mode."""
        # Complex tasks get detailed format
        if result.get("route") in ["fleet_complex", "fleet_multi"]:
            return "detailed"

        # Failed/blocked tasks get detailed explanation
        if result.get("status") in ["failed", "blocked"]:
            return "detailed"

        # Long execution time suggests detailed
        if result.get("execution_time_seconds", 0) > 30:
            return "detailed"

        # Safety-critical tasks
        if result.get("route") == "fleet_safety":
            return "detailed"

        # Default to summary
        return "summary"

    def _format_minimal(self, result: Dict[str, Any]) -> str:
        """Minimal one-line format."""
        status = result.get("status", "unknown")
        emoji = self.STATUS_EMOJIS.get(status, "❓")
        task_id = result.get("task_id", "unknown")[:8]

        return f"{emoji} [{task_id}] {status.title()}"

    def _format_summary(
        self,
        result: Dict[str, Any],
        platform: str
    ) -> str:
        """Summary format for quick tasks."""
        status = result.get("status", "unknown")
        emoji = self.STATUS_EMOJIS.get(status, "❓")
        route = result.get("route", "unknown")
        route_icon = self.ROUTE_ICONS.get(route, "❓")

        lines = [
            f"{emoji} **Task {status.upper()}**",
            f"",
        ]

        # Add timing
        exec_time = result.get("execution_time_seconds", 0)
        if exec_time > 0:
            lines.append(f"⏱️ {exec_time:.1f}s")

        # Add result summary if available
        task_result = result.get("result", {})
        if summary := task_result.get("summary"):
            lines.append(f"")
            lines.append(f"📋 {summary}")

        return "\n".join(lines)

    def _format_detailed(
        self,
        result: Dict[str, Any],
        platform: str
    ) -> str:
        """Detailed format for complex tasks."""
        status = result.get("status", "unknown")
        emoji = self.STATUS_EMOJIS.get(status, "❓")
        route = result.get("route", "unknown")
        route_icon = self.ROUTE_ICONS.get(route, "⚡")

        lines = [
            f"{emoji} **Task {status.upper()}**",
            f"━━━━━━━━━━━━━━━━━━━━━",
            f"",
        ]

        # Task ID
        task_id = result.get("task_id", "unknown")
        lines.append(f"🆔 `{task_id}`")

        # Timing
        lines.append(f"")
        exec_time = result.get("execution_time_seconds", 0)
        if exec_time > 0:
            lines.append(f"⏱️ **Duration**: {exec_time:.1f}s")

        created = result.get("created_at", "")
        completed = result.get("completed_at", "")
        if created and completed:
            lines.append(f"🕐 **Started**: {self._format_time(created)}")
            lines.append(f"🕐 **Completed**: {self._format_time(completed)}")

        # Safety & QA
        lines.append(f"")
        if "safety_passed" in result:
            safety_emoji = "✅" if result["safety_passed"] else "❌"
            lines.append(f"{safety_emoji} **Safety Check**: {'Passed' if result['safety_passed'] else 'Failed'}")

        if "qa_passed" in result:
            qa_emoji = "✅" if result["qa_passed"] else "⚠️"
            lines.append(f"{qa_emoji} **QA Gate**: {'Passed' if result['qa_passed'] else 'Issues Found'}")

        # Result content
        task_result = result.get("result", {})

        if summary := task_result.get("summary"):
            lines.append(f"")
            lines.append(f"📋 **Summary**:")
            lines.append(f"{summary}")

        # Error handling
        if error := result.get("error_message"):
            lines.append(f"")
            lines.append(f"❌ **Error**:")
            lines.append(f"```")
            lines.append(f"{error[:500]}")
            lines.append(f"```")

            # Add suggestions
            lines.append(f"")
            lines.append(f"💡 **Suggestions**:")
            lines.extend(self._generate_suggestions(result))

        return "\n".join(lines)

    def _format_time(self, iso_time: str) -> str:
        """Format ISO timestamp to readable string."""
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except:
            return iso_time

    def _generate_suggestions(self, result: Dict[str, Any]) -> List[str]:
        """Generate actionable suggestions for errors."""
        suggestions = []
        error = result.get("error_message", "").lower()
        status = result.get("status", "")

        if status == "blocked":
            suggestions.append("• Review task for safety concerns")
            suggestions.append("• Consider rephrasing to avoid sensitive keywords")
            suggestions.append("• Use `/fleet plan` to check execution path first")

        elif "timeout" in error:
            suggestions.append("• Task took too long - try breaking into smaller tasks")
            suggestions.append("• Check if resources are available")

        elif "connection" in error:
            suggestions.append("• Fleet may be temporarily unavailable")
            suggestions.append("• Retry with `/fleet run` after a moment")

        elif "not found" in error:
            suggestions.append("• Verify task ID is correct")
            suggestions.append("• Use `/fleet tasks` to list recent tasks")

        else:
            suggestions.append("• Check logs for detailed error")
            suggestions.append("• Try running with dry-run first: `/fleet plan \"task\"`")

        return suggestions

    def format_fleet_status(self, health: Dict[str, Any]) -> str:
        """Format fleet health status for display."""
        ready = health.get("ready", False)
        status_emoji = "🟢" if ready else "🔴"

        lines = [
            f"{status_emoji} **Fleet Status**",
            f"━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"**Status**: {health.get('status', 'unknown').upper()}",
            f"**Version**: {health.get('version', 'unknown')}",
            f"",
            f"📊 **Agents**:",
            f"   • Main Agents: {health.get('main_agents', 0)}",
            f"   • Sub Agents: {health.get('sub_agents', 0)}",
            f"   • Total: {health.get('main_agents', 0) + health.get('sub_agents', 0)}",
        ]

        # Divisions
        divisions = health.get('divisions', [])
        if divisions:
            lines.append(f"")
            lines.append(f"🏢 **Divisions**: {', '.join(divisions[:4])}")
            if len(divisions) > 4:
                lines[-1] += f", ... ({len(divisions) - 4} more)"

        # Safety & QA
        lines.append(f"")
        safety = health.get('safety_core', {})
        qa = health.get('qa_gate', {})

        if safety.get('enabled'):
            lines.append(f"🛡️ **Safety Core**: {safety.get('status', 'unknown')}")
        if qa.get('enabled'):
            lines.append(f"🔍 **QA Gate**: {qa.get('status', 'unknown')}")

        return "\n".join(lines)

    def format_os_status(self, status: Dict[str, Any]) -> str:
        """Format Hermes OS status in the shared sectioned layout."""
        mode = status.get("mode", "unknown")
        active = bool(status.get("active"))
        components = status.get("components", {}) or {}
        fleet = status.get("fleet") or {}
        auto_run = status.get("auto_run") or {}
        telemetry = status.get("telemetry") or {}
        policy = status.get("policy") or {}
        memory = status.get("memory") or {}
        mcp = status.get("mcp") or {}

        gateway_running = bool(components.get("gateway"))
        gateway = "running" if gateway_running else "stopped"
        fleet_ready = bool(components.get("fleet"))
        rtk_ready = bool(components.get("rtk"))
        context7_ready = bool(
            components.get("context7")
            or (mcp.get("context7") or {}).get("enabled")
        )
        context_mode_ready = bool(
            components.get("context_mode")
            or (mcp.get("context_mode") or {}).get("enabled")
        )
        timezone = "Asia/Bangkok"
        auto_run_mode = str(auto_run.get("mode", "off"))
        auto_run_state = auto_run.get("state") or {}
        auto_run_last_cycle = auto_run_state.get("last_cycle_id") or "none"
        auto_run_kill_switch = "on" if auto_run_state.get("kill_switch") else "off"
        telemetry_cached = telemetry.get("events_cached", 0)
        telemetry_path = telemetry.get("telemetry_path", "unknown")
        policy_id = policy.get("active_id", "unknown")
        policy_seq = policy.get("active_sequence", "unknown")
        policy_status = policy.get("status", "unknown")
        memory_tasks = memory.get("tasks_count", 0)

        lines = [
            "🛰️ Hermes OS Status",
            "━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🧭 Mode",
            f"  • Name: Hermes OS",
            f"  • Value: {mode}",
            "",
            "⚡ Active",
            f"  • Status: {'Yes' if active else 'No'}",
            f"  • Gateway: {gateway}",
            f"  • RTK: {'Enabled' if rtk_ready else 'Disabled'}",
            "",
            "🧠 Control Layer",
            "  • Role: nervous/control layer for actions",
            "  • Core Body: Hermes Agent",
            "  • Execution: Direct by default",
            "  • Router: Retired",
            "  • Limbs: Fleet / thClaws / OMX via explicit or policy-approved actions",
            "",
            "⚙️ Components",
            f"  • Fleet: {'Ready' if fleet_ready else 'Not ready'}",
            f"  • RTK: {'Ready' if rtk_ready else 'Not ready'}",
            f"  • Context Mode: {'Ready' if context_mode_ready else 'Not ready'}",
            f"  • Context7: {'Ready' if context7_ready else 'Not ready'} (external docs evidence)",
            f"  • Timezone: {timezone}",
            "",
            "🚀 Fleet",
            f"  • Main Agents: {fleet.get('main_agents', 0)}",
            f"  • Sub Agents: {fleet.get('sub_agents', 0)}",
            "  • Mode: Manual/explicit execution limb",
            "",
            "🔁 Auto-run",
            f"  • Mode: {auto_run_mode}",
            f"  • Kill Switch: {auto_run_kill_switch}",
            f"  • Last Cycle: {auto_run_last_cycle}",
            "",
            "📡 Telemetry",
            f"  • Cached Events: {telemetry_cached}",
            f"  • Telemetry Path: {telemetry_path}",
            "",
            "📚 Policy",
            f"  • Active ID: {policy_id}",
            f"  • Sequence: {policy_seq}",
            f"  • Status: {policy_status}",
            "",
            "🧠 Memory",
            f"  • Tasks Count: {memory_tasks}",
        ]

        if auto_run_last_cycle != "none":
            lines.extend([
                "",
                f"ℹ️ Auto-run ledger: {auto_run_state.get('updated_reason', 'unknown')}",
            ])

        return "\n".join(lines)

    def format_task_list(
        self,
        tasks: List[Dict[str, Any]],
        limit: int = 10
    ) -> str:
        """Format list of tasks for display."""
        lines = [
            f"📋 **Recent Tasks**",
            f"━━━━━━━━━━━━━━━━━━━━━",
            f"",
        ]

        if not tasks:
            lines.append("No recent tasks found.")
            return "\n".join(lines)

        for i, task in enumerate(tasks[:limit], 1):
            status = task.get("status", "unknown")
            emoji = self.STATUS_EMOJIS.get(status, "❓")
            task_id = task.get("task_id", "unknown")[:8]
            desc = task.get("description", "No description")[:40]

            lines.append(f"{i}. {emoji} `{task_id}` - {desc}...")

        if len(tasks) > limit:
            lines.append(f"")
            lines.append(f"... and {len(tasks) - limit} more tasks")

        return "\n".join(lines)

    def format_routing_decision(
        self,
        decision: Any,
        task: str
    ) -> str:
        """Routing analysis is unavailable in direct mode."""
        return "❌ Hermes OS direct mode only."


# Convenience functions
def format_result(
    result: Dict[str, Any],
    mode: str = "auto",
    platform: str = "telegram"
) -> str:
    """Format result (convenience function)."""
    formatter = ResponseFormatter()
    return formatter.format(result, mode, platform)


def format_status(health: Dict[str, Any]) -> str:
    """Format fleet status (convenience function)."""
    formatter = ResponseFormatter()
    return formatter.format_fleet_status(health)


def format_os_status(status: Dict[str, Any]) -> str:
    """Format Hermes OS status (convenience function)."""
    formatter = ResponseFormatter()
    return formatter.format_os_status(status)


def format_tasks(tasks: List[Dict[str, Any]], limit: int = 10) -> str:
    """Format task list (convenience function)."""
    formatter = ResponseFormatter()
    return formatter.format_task_list(tasks, limit)


if __name__ == "__main__":
    # Test formatting
    formatter = ResponseFormatter()

    # Test completed task
    result = {
        "task_id": "fleet_abc123",
        "status": "completed",
        "route": "fleet_complex",
        "division": "DIV-02",
        "main_agent": "Chief Engineering Agent",
        "sub_agents_used": ["Backend Agent", "Frontend Agent", "DevOps Agent"],
        "execution_time_seconds": 45.5,
        "safety_passed": True,
        "qa_passed": True,
        "result": {"summary": "REST API built with auth and rate limiting"},
    }

    print("=== DETAILED FORMAT ===")
    print(formatter.format(result, mode="detailed"))
    print("\n")

    print("=== SUMMARY FORMAT ===")
    print(formatter.format(result, mode="summary"))
    print("\n")

    # Test blocked task
    blocked = {
        "task_id": "fleet_def456",
        "status": "blocked",
        "route": "fleet_safety",
        "division": "DIV-05",
        "error_message": "Detected unsafe pattern: 'delete all'",
        "safety_passed": False,
    }

    print("=== BLOCKED TASK ===")
    print(formatter.format(blocked, mode="detailed"))
