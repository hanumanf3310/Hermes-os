# -*- coding: utf-8 -*-
"""
Hermes OS Telegram Integration

Automatically routes Boss messages through Hermes OS when in hermes-os mode.
This module bridges Hermes Gateway (Telegram) with Hermes OS.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Setup path for Hermes OS
HERMES_OS_DIR = Path.home() / ".hermes" / "os"
if str(HERMES_OS_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_OS_DIR))

# Import Hermes OS
from hermes_os import HermesOS, get_os

logger = logging.getLogger(__name__)


class HermesOSTelegramBridge:
    """
    Bridge between Hermes Gateway (Telegram) and Hermes OS.

    Automatically detects hermes-os mode and routes tasks accordingly:
    - hermes_os mode ON: Tasks go through HermesOS.execute() → Fleet/Hermes
    - hermes_os mode OFF: Normal Hermes processing

    This is the main integration point for Telegram messaging.
    """

    def __init__(self):
        self._os: Optional[HermesOS] = None
        self._mode: str = "hermes_off"
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the bridge and check if Hermes OS mode is active.

        Returns:
            True if Hermes OS mode is active and ready
        """
        try:
            # Check state file for mode
            state_file = Path.home() / ".hermes" / "state" / "hermes-os.json"

            if state_file.exists():
                state = json.loads(state_file.read_text())
                self._mode = state.get("mode", "hermes_off")

                if self._mode == "hermes_os":
                    # Initialize Hermes OS
                    self._os = get_os()
                    self._initialized = True
                    logger.info("🛰️ Hermes OS Telegram Bridge initialized")
                    logger.info(f"   Mode: {self._mode}")
                    logger.info(f"   Fleet: {self._os.fleet.main_agents}M/{self._os.fleet.sub_agents}S agents")
                    return True
                else:
                    logger.info(f"Hermes OS mode is OFF ({self._mode}), using normal Hermes")
                    return False
            else:
                logger.info("No hermes-os state file found, Hermes OS not active")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Hermes OS Bridge: {e}")
            return False

    def is_os_mode_active(self) -> bool:
        """Check if Hermes OS mode is currently active."""
        return self._initialized and self._mode == "hermes_os" and self._os is not None

    def process_message(
        self,
        message: str,
        boss_id: str,
        boss_name: str,
        chat_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """
        Process a message from Boss through Hermes OS.

        This is the main entry point for Telegram messages when Hermes OS
        mode is active.

        Args:
            message_text: The message from Boss
            boss_id: Boss identifier
            boss_name: Boss display name
            chat_id: Telegram chat ID

        Returns:
            Dict with 'response' (str) and 'metadata' (dict)

        Example:
            >>> bridge = HermesOSTelegramBridge()
            >>> result = bridge.process_message("Build API", "user123", "Boss")
            >>> print(result['response'])
        """
        if not self.is_os_mode_active():
            # Return None to indicate normal Hermes should handle
            return {
                "handled": False,
                "response": None,
                "reason": "Hermes OS mode not active"
            }

        context = context or {}
        message_text = message
        logger.info(f"Processing message via Hermes OS: {message_text[:50]}...")

        # Build context for the task
        base_context = {
            "boss_id": boss_id,
            "boss_name": boss_name,
            "chat_id": chat_id,
            "platform": "telegram",
            "timestamp": self._now(),
            "message": message_text,
            "raw_task": message_text,
        }
        # Keep caller-provided fields as override so integrations can force values explicitly.
        context = {**base_context, **context}

        # Let normal Hermes Gateway handle direct/simple chat. Hermes OS only handles
        # explicit Fleet overrides now that automatic analysis has been removed.
        if self._should_defer_to_gateway(message_text, context):
            return {
                "handled": False,
                "response": None,
                "reason": "Hermes OS disabled; defer to gateway agent",
            }

        # Execute through Hermes OS for Fleet/safety routes.
        try:
            result = self._os.execute(message_text, context)

            # Format response for Telegram
            response = self._format_response(result)

            return {
                "handled": True,
                "response": response,
                "metadata": {
                    "task_id": result.get("task_id"),
                    "route": result.get("route"),
                    "status": result.get("status"),
                }
            }

        except Exception as e:
            logger.error(f"Error executing through Hermes OS: {e}")
            return {
                "handled": True,
                "response": f"❌ Error: {str(e)[:200]}",
                "metadata": {"error": str(e)}
            }

    def _should_defer_to_gateway(self, message_text: str, context: Dict[str, Any]) -> bool:
        """Return True when normal Hermes should answer instead of Hermes OS execution."""
        try:
            if not self._os:
                return True

            manual_override = context.get("manual_override")
            if not isinstance(manual_override, str):
                raw_text = (message_text or "").strip().lower()
                if raw_text.startswith("/fleet") or raw_text.startswith("/hermes-os fleet"):
                    context["manual_override"] = "fleet"
                    manual_override = "fleet"
            return manual_override != "fleet"
        except Exception as e:
            logger.warning(f"Could not preflight Hermes OS route; using Hermes OS bridge: {e}")
            return False

    def _format_response(self, result: Dict[str, Any]) -> str:
        """Format execution result for Telegram display."""
        try:
            from core.response_formatter import ResponseFormatter
            formatter = ResponseFormatter()
            return formatter.format(result, mode="auto", platform="telegram")
        except ImportError:
            # Fallback formatting
            return self._fallback_format(result)

    def _fallback_format(self, result: Dict[str, Any]) -> str:
        """Simple fallback formatting."""
        status = result.get("status", "unknown")
        status_emoji = {"completed": "✅", "failed": "❌", "blocked": "🚫"}.get(status, "❓")

        lines = [
            f"{status_emoji} **Task {status.upper()}**",
            "",
        ]

        if task_result := result.get("result", {}).get("summary"):
            lines.append("")
            lines.append(f"📋 {task_result}")

        if error := result.get("error_message"):
            lines.append(f"")
            lines.append(f"❌ Error: {error[:200]}")

        return "\n".join(lines)

    def _now(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status."""
        return {
            "initialized": self._initialized,
            "mode": self._mode,
            "os_active": self.is_os_mode_active(),
            "fleet_health": self._os.fleet.health() if self._os and self._os.fleet else None
        }

    def capture_routing_feedback(
        self,
        task_id: str,
        label: str,
        note: str = "",
        source: str = "telegram",
    ) -> Dict[str, Any]:
        """Capture routing feedback for a given task_id."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.capture_routing_feedback(task_id, label, note=note, source=source)

    def get_feedback_metrics(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Return feedback capture and routing mix metrics from Hermes OS telemetry."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        metrics = self._os.get_routing_feedback_metrics(limit=limit)
        metrics["ok"] = True
        return metrics

    def get_policy_status(self) -> Dict[str, Any]:
        """Return Hermes OS learning policy summary."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return {"ok": True, "policy_status": self._os.get_policy_status()}

    def propose_policy(self, policy_overrides: Dict[str, Any], rationale: str = "", source: str = "telegram") -> Dict[str, Any]:
        """Propose a new learning policy candidate."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.propose_learning_policy(policy_overrides, rationale=rationale, source=source)

    def apply_policy(self, policy_id: str, reason: str = "manual-approval") -> Dict[str, Any]:
        """Apply a policy candidate as active."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.apply_learning_policy(policy_id, reason=reason)

    def evaluate_policy_readiness(self, policy_id: str, limit: Optional[int] = None, min_feedback_events: int = 20) -> Dict[str, Any]:
        """Check readiness for a policy candidate before applying."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.evaluate_learning_policy_readiness(
            policy_id,
            limit=limit,
            min_feedback_events=min_feedback_events,
        )

    def evaluate_learning_policy_candidates(self, limit: Optional[int] = None, min_feedback_events: int = 20) -> Dict[str, Any]:
        """Evaluate multiple candidate policies for offline replay/readiness in one pass (Phase D)."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.evaluate_learning_policy_candidates(
            limit=limit,
            min_feedback_events=min_feedback_events,
        )

    def assess_active_policy_health(self, min_feedback_events: int = 20) -> Dict[str, Any]:
        """Assess active policy drift/rollback risk using feedback telemetry."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.assess_active_policy_health(min_feedback_events=min_feedback_events)

    def propose_guarded_auto_tune(self, min_feedback_events: int = 20) -> Dict[str, Any]:
        """Run guarded auto-tuning recommendations (Phase E)."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.propose_guarded_auto_tune(min_feedback_events=min_feedback_events)

    def get_auto_run_status(self) -> Dict[str, Any]:
        """Return auto-run control-plane status."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        status = self._os.get_auto_run_status()
        status["ok"] = True
        return status

    def set_auto_run_mode(self, mode: str, actor: str = "operator", reason: str = "") -> Dict[str, Any]:
        """Set auto-run mode: off | pilot | auto."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.set_auto_run_mode(mode=mode, actor=actor, reason=reason)

    def run_learning_control_cycle(
        self,
        limit: Optional[int] = None,
        min_feedback_events: int = 20,
        actor: str = "operator",
        source: str = "manual",
    ) -> Dict[str, Any]:
        """Execute one Option-7 control-cycle evaluation (safe, no auto-apply side effects)."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.run_learning_control_cycle(
            limit=limit,
            min_feedback_events=min_feedback_events,
            actor=actor,
            source=source,
        )

    def run_auto_learning_loop(
        self,
        limit: Optional[int] = None,
        min_feedback_events: int = 20,
        actor: str = "operator",
        source: str = "scheduler",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Execute one auto-run loop cycle honoring mode/kill/cooldown gates."""
        if not self.is_os_mode_active():
            return {"ok": False, "error": "Hermes OS mode is OFF"}
        return self._os.run_auto_learning_loop(
            limit=limit,
            min_feedback_events=min_feedback_events,
            actor=actor,
            source=source,
            force=force,
        )

    def refresh_mode(self) -> bool:
        """
        Refresh mode from state file (call when mode may have changed).

        Returns:
            True if mode changed
        """
        old_mode = self._mode

        state_file = Path.home() / ".hermes" / "state" / "hermes-os.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            new_mode = state.get("mode", "hermes_off")

            if new_mode != old_mode:
                self._mode = new_mode
                if new_mode == "hermes_os":
                    self.initialize()
                else:
                    self._os = None
                    self._initialized = False
                logger.info(f"Mode changed: {old_mode} → {new_mode}")
                return True

        return False




# Global bridge instance (singleton)
_bridge_instance: Optional[HermesOSTelegramBridge] = None


def get_bridge() -> HermesOSTelegramBridge:
    """Get or create bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = HermesOSTelegramBridge()
        _bridge_instance.initialize()
    return _bridge_instance


def set_bridge(bridge: HermesOSTelegramBridge):
    """Set global bridge instance."""
    global _bridge_instance
    _bridge_instance = bridge


def process_via_os(
    message: str,
    boss_id: str,
    boss_name: str = "Boss",
    chat_id: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to process a message via Hermes OS.

    Returns:
        Formatted response string, or None if OS mode not active

    Example:
        >>> response = process_via_os("Build API", "user123")
        >>> if response:
        ...     send_to_telegram(response)
        ... else:
        ...     # Handle with normal Hermes
    """
    bridge = get_bridge()

    # Refresh mode check
    bridge.refresh_mode()

    if not bridge.is_os_mode_active():
        return None

    result = bridge.process_message(message, boss_id, boss_name, chat_id)

    if result["handled"]:
        return result["response"]

    return None


# Command handlers for Telegram integration

def handle_hermes_os_command(command: str, args: str) -> str:
    """
    Handle /hermes-os commands from Telegram.

    Commands:
        /hermes-os status     - Show OS status
        /hermes-os fleet      - Show Fleet status
        /hermes-os refresh    - Reload mode file
    /hermes-os feedback   - Record routing feedback: <task_id> <label> [note]
    /hermes-os metrics    - Show feedback + routing telemetry metrics
    /hermes-os policy     - Show policy summary / candidate status
    /hermes-os propose    - Create policy candidate: /hermes-os propose <json>
    /hermes-os apply     - Apply policy: /hermes-os apply <policy_id> [reason]
    /hermes-os readiness  - Check policy: /hermes-os readiness <policy_id> [min_samples]
    /hermes-os replay    - Evaluate all candidate policies (offline replay/readiness): /hermes-os replay [limit] [min_samples]
    /hermes-os health    - Assess active policy drift/rollback risk
    /hermes-os tune      - Guarded auto-tune recommendation (read-only)
    """
    bridge = get_bridge()

    def _format_metrics(text_metrics: Dict[str, Any]) -> str:
        if not text_metrics.get("ok", True):
            return f"❌ {text_metrics.get('error', 'unknown error')}"

        lines = [
            "📊 **Hermes OS Feedback Metrics**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"event_total: {text_metrics.get('feedback_total', 0)}",
            f"feedback_total: {text_metrics.get('feedback_total', 0)}",
            f"manual_override_rate: {text_metrics.get('manual_override_rate', 0):.2%}",
            "",
        ]

        feedback = text_metrics.get("feedback", {})
        labels = feedback.get("labels", {})
        fp = feedback.get("false_positive", {})
        lines.extend([
            "**Feedback Labels:**",
            f"  - correct: {labels.get('correct', 0)}",
            f"  - incorrect: {labels.get('incorrect', 0)}",
            f"  - should_direct: {labels.get('should_direct', 0)}",
            f"  - should_fleet: {labels.get('should_fleet', 0)}",
            "",
            "**False Positive Signals:**",
            f"  - should_direct: {fp.get('should_direct', {}).get('count', 0)} (rate {fp.get('should_direct', {}).get('rate', 0):.2%})",
            f"  - should_fleet: {fp.get('should_fleet', {}).get('count', 0)} (rate {fp.get('should_fleet', {}).get('rate', 0):.2%})",
            f"  - total: {fp.get('total', 0)} (rate {fp.get('rate', 0):.2%})",
        ])
        return "\n".join(lines)

    if command == "status":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF\n\nUse `hermes-os` command in terminal to activate."

        try:
            from core.response_formatter import format_os_status
            status = bridge._os.status() if bridge._os else {"active": False}
            return format_os_status(status)
        except Exception as e:
            return f"❌ Error getting OS status: {e}"

    elif command == "fleet":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        try:
            from core.response_formatter import format_status
            health = bridge._os.fleet.health()
            return format_status(health)
        except Exception as e:
            return f"❌ Error getting fleet status: {e}"

    elif command == "refresh":
        changed = bridge.refresh_mode()
        mode = bridge._mode
        return f"🔄 Mode refreshed: {mode}" + (" (changed!)" if changed else "")

    elif command == "feedback":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split(maxsplit=2)
        if len(parts) < 2:
            return "❗ Usage: /hermes-os feedback <task_id> <label> [note]\n\nLabels: correct, incorrect, should_direct, should_fleet"

        task_id, label = parts[0], parts[1]
        note = parts[2] if len(parts) >= 3 else ""
        result = bridge.capture_routing_feedback(task_id=task_id, label=label, note=note)
        if result.get("ok"):
            return f"✅ Feedback captured for `{task_id}` → {label}"
        return f"❌ Feedback error: {result.get('error')}"

    elif command == "metrics":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"
        arg = args.strip()
        limit = None
        if arg:
            try:
                limit = max(1, int(arg))
            except ValueError:
                return "❗ Usage: /hermes-os metrics [limit]"
        metrics = bridge.get_feedback_metrics(limit=limit)
        return _format_metrics(metrics)

    elif command == "policy":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"
        status = bridge.get_policy_status()
        if not status.get("ok"):
            return f"❌ {status.get('error')}"

        policy = status.get("policy_status", {})
        active = policy.get("active", {})
        lines = [
            "📚 **Hermes OS Learning Policy**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"Active: {active.get('policy_id', 'unknown')} ({active.get('status', 'unknown')})",
            f"Policy sequence: {active.get('policy_sequence', 'unknown')}",
            f"Source: {active.get('source', 'unknown')}",
            f"Store: {policy.get('store_path', '-')}",
            f"Candidates: {policy.get('candidates', 0)} / Total: {policy.get('total_records', 0)}",
        ]
        return "\n".join(lines)

    elif command == "propose":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        try:
            payload = json.loads(args.strip()) if args.strip() else None
        except Exception:
            return "❗ Usage: /hermes-os propose '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91}'"

        if not isinstance(payload, dict):
            return "❗ Usage: /hermes-os propose '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91}'"

        reason = ""
        if "rationale" in payload:
            reason = str(payload.pop("rationale"))

        result = bridge.propose_policy(payload, rationale=reason)
        if not result.get("ok"):
            return f"❌ Policy propose error: {result.get('error')}"

        policy = result.get("policy", {})
        return "✅ Policy proposed: " + f"{policy.get('policy_id')} (seq {policy.get('policy_sequence')})"

    elif command == "apply":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split(maxsplit=1)
        if not parts:
            return "❗ Usage: /hermes-os apply <policy_id> [reason]"
        policy_id = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else "manual-approval"
        result = bridge.apply_policy(policy_id, reason=reason)
        if not result.get("ok"):
            return f"❌ Policy apply error: {result.get('error')}"
        return f"✅ Policy applied: {policy_id}"

    elif command == "readiness":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split()
        if not parts:
            return "❗ Usage: /hermes-os readiness <policy_id> [min_samples]"

        policy_id = parts[0].strip()
        min_samples = 20
        if len(parts) > 1:
            try:
                min_samples = max(1, int(parts[1]))
            except ValueError:
                return "❗ Usage: /hermes-os readiness <policy_id> [min_samples]"

        status = bridge.evaluate_policy_readiness(policy_id, min_feedback_events=min_samples)
        if not status.get("ok"):
            return f"❌ Policy readiness error: {status.get('reason_codes', []) or status.get('error')}"

        notes = " | ".join(status.get("reason_codes", []) or [])
        if status.get("ready"):
            return f"✅ Policy {policy_id} ready for offline replay validation"
        return f"⚠️ {policy_id} not ready: {notes}"

    elif command == "replay":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split()
        limit = None
        min_samples = 20
        if parts:
            try:
                if len(parts) >= 1:
                    limit = int(parts[0])
                if len(parts) >= 2:
                    min_samples = max(1, int(parts[1]))
            except ValueError:
                return "❗ Usage: /hermes-os replay [limit] [min_samples]"

        status = bridge.evaluate_learning_policy_candidates(limit=limit, min_feedback_events=min_samples)
        if not status.get("ok"):
            return f"❌ Replay command error: {status.get('error', 'unknown')}"

        lines = [
            "🛰️ **Hermes OS Replay Evaluation**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"Evaluated: {status.get('evaluated_count', 0)}",
            f"Ready: {status.get('ready_count', 0)} / Blocked: {status.get('blocked_count', 0)}",
            "",
        ]

        for row in status.get("evaluations", [])[:10]:
            status_marker = "✅" if row.get("ready") else "⚠️"
            reason_text = ", ".join(row.get("reason_codes", []))
            lines.append(
                f"{status_marker} {row.get('policy_id', 'unknown')} "
                f"({row.get('observed_feedback_total', 0)}/{row.get('required_feedback_total', min_samples)})"
            )
            if reason_text:
                lines.append(f"   reason: {reason_text}")

        return "\n".join(lines)

    elif command == "health":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split()
        min_samples = 20
        if parts:
            try:
                min_samples = max(1, int(parts[0]))
            except ValueError:
                return "❗ Usage: /hermes-os health [min_samples]"

        status = bridge.assess_active_policy_health(min_feedback_events=min_samples)
        if not status.get("ok"):
            return f"⚠️ Active policy health: {status.get('error', 'insufficient_feedback')}"

        state = "🚨" if status.get("rollback_trigger") else "✅"
        return (
            f"{state} Rollback trigger: {status.get('rollback_trigger')}\n"
            f"risk_level: {status.get('risk_level')}\n"
            f"manual_override_rate: {status.get('manual_override_rate', 0):.2%}\n"
            f"false_positive_rate: {status.get('false_positive_rate', 0):.2%}"
        )

    elif command == "tune":
        if not bridge.is_os_mode_active():
            return "🔴 Hermes OS mode is OFF"

        parts = args.split()
        min_samples = 20
        if parts:
            try:
                min_samples = max(1, int(parts[0]))
            except ValueError:
                return "❗ Usage: /hermes-os tune [min_samples]"

        status = bridge.propose_guarded_auto_tune(min_feedback_events=min_samples)
        if not status.get("ok"):
            return f"❌ Guarded tuning unavailable: {status.get('error', 'unknown')}"

        if status.get("rollback_trigger"):
            return "⚠️ Guarded tuning blocked (rollback risk): " + ", ".join(status.get("reason_codes", []))

        lines = [
            "🧠 **Hermes OS Guarded Tuning**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"apply_recommended: {'true' if status.get('apply_recommended') else 'false'}",
        ]
        for code in status.get("reason_codes", []):
            lines.append(f"- {code}")
        for item in status.get("suggestions", []):
            lines.append(f"• {item.get('type')}: {item.get('from')} -> {item.get('to')} ({item.get('rationale')})")

        return "\n".join(lines)

    else:
        return """🛰️ **Hermes OS Commands**
━━━━━━━━━━━━━━━━━━━━━

/hermes-os status   - Show OS status
/hermes-os fleet    - Show Fleet status
/hermes-os feedback - Capture routing feedback: /hermes-os feedback <task_id> <label> [note]
/hermes-os metrics  - Show feedback metrics
/hermes-os policy   - Show learning policy status
/hermes-os propose  - Propose policy candidate from JSON payload
/hermes-os apply    - Apply policy id
/hermes-os readiness - Evaluate policy readiness
/hermes-os replay   - Replay candidate policies: /hermes-os replay [limit] [min_samples]
/hermes-os health   - Assess active policy rollback risk
/hermes-os tune     - Guarded auto-tuning recommendations
/hermes-os refresh  - Refresh mode check

Messages automatically route through Hermes OS when mode is active."""



if __name__ == "__main__":
    # Test the bridge
    bridge = HermesOSTelegramBridge()

    if bridge.initialize():
        print("✅ Hermes OS Bridge initialized")

        # Test message processing
        result = bridge.process_message(
            "Build REST API with authentication",
            boss_id="test_user",
            boss_name="Test Boss"
        )

        print("\n📨 Processed Message:")
        print(result['response'])
    else:
        print("🔴 Hermes OS mode not active")
        print("Run `hermes-os` command in terminal to activate")
