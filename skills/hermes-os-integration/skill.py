"""
hermes-os-integration skill for Hermes Agent

Provides automatic integration with Hermes OS when in hermes_os mode.
Non-invasive, safe, and version-independent.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

# Hermes OS path setup
HERMES_OS_DIR = Path.home() / ".hermes" / "os"
if str(HERMES_OS_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_OS_DIR))

# Skill metadata
SKILL_NAME = "hermes-os-integration"
SKILL_VERSION = "1.0.0"


class HermesOSSkill:
    """
    Skill that provides Hermes OS integration.
    
    Auto-detects Hermes OS mode and provides commands:
    - hermes-os: Show status and policy controls
    - hermes-learning: Manual learning control (operator-triggered only)
    - fleet: Route tasks to Fleet
    
    This skill is non-invasive and safe to load even when
    Hermes OS mode is not active.
    """
    
    def __init__(self, hermes_context=None):
        """
        Initialize the skill.
        
        Args:
            hermes_context: Optional Hermes context object
        """
        self.context = hermes_context
        self._bridge = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        Initialize and check if Hermes OS is active.
        
        Returns:
            True if Hermes OS mode is active
        """
        try:
            # Check state file
            state_file = Path.home() / ".hermes" / "state" / "hermes-os.json"
            
            if not state_file.exists():
                logger.info(f"[{SKILL_NAME}] Hermes OS state not found, skill inactive")
                return False
            
            state = json.loads(state_file.read_text())
            mode = state.get("mode", "hermes_off")
            
            if mode != "hermes_os":
                logger.info(f"[{SKILL_NAME}] Hermes OS mode is OFF ({mode}), skill inactive")
                return False
            
            # Try to import and initialize bridge
            try:
                from integrations.telegram_bridge import HermesOSTelegramBridge
                self._bridge = HermesOSTelegramBridge()
                self._initialized = self._bridge.initialize()
                
                if self._initialized:
                    logger.info(f"[{SKILL_NAME}] ✓ Hermes OS bridge initialized")
                    logger.info(f"   Fleet: {self._bridge._os.fleet.main_agents}M/{self._bridge._os.fleet.sub_agents}S agents")
                    return True
                else:
                    logger.warning(f"[{SKILL_NAME}] Bridge initialization failed")
                    return False
                    
            except ImportError as e:
                logger.error(f"[{SKILL_NAME}] Cannot import bridge: {e}")
                return False
                
        except Exception as e:
            logger.error(f"[{SKILL_NAME}] Initialization error: {e}")
            return False
    
    def is_active(self) -> bool:
        """Check if Hermes OS mode is currently active."""
        return self._initialized and self._bridge is not None and self._bridge.is_os_mode_active()
    
    def handle_command(self, command: str, args: str = "") -> Optional[str]:
        """
        Handle skill-specific commands.
        
        Args:
            command: The command (e.g., "hermes-os", "fleet")
            args: Additional arguments
            
        Returns:
            Response string or None if not handled
        """
        if not self.is_active():
            return None
        
        # Refresh mode check
        self._bridge.refresh_mode()
        
        if not self.is_active():
            return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."
        
        # Handle commands
        if command == "hermes-os":
            return self._handle_hermes_os_command(args)
        
        elif command == "hermes-learning":
            return self._handle_hermes_learning_command(args)

        elif command == "fleet":
            return self._handle_fleet_command(args)
        
        return None
    
    def _handle_hermes_learning_command(self, args: str) -> str:
        """Manual learning control command (explicit operator trigger only)."""
        args_parts = args.split()
        if not args_parts:
            return (
                "🧠 **Hermes Learning (Manual)**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "Auto learning is disabled.\n"
                "Run explicitly:\n"
                "- hermes-learning run [limit] [min_samples]\n"
                "- hermes-learning status\n"
                "- hermes-learning ingest feedback <task_id> <label> [note]\n"
                "- hermes-learning ingest policy <json>\n"
                "- hermes-learning ingest note <text> [--link <url>] [--file <path>] [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]"
            )

        action = args_parts[0].lower()
        if action == "status":
            result = self._bridge.get_auto_run_status()
            if not result.get("ok"):
                return f"❌ Learning status error: {result.get('error', 'unknown')}"
            state = result.get("state", {}) or {}
            return (
                "🧠 **Hermes Learning (Manual)**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"Auto mode: {state.get('mode', 'off')}\n"
                f"Kill-switch: {'ON' if state.get('kill_switch', False) else 'OFF'}\n"
                "Control: operator-triggered only"
            )

        if action == "run":
            limit = None
            min_samples = 20
            if len(args_parts) > 1:
                try:
                    limit = int(args_parts[1])
                except ValueError:
                    return "❗ Usage: hermes-learning run [limit] [min_samples]"
            if len(args_parts) > 2:
                try:
                    min_samples = max(1, int(args_parts[2]))
                except ValueError:
                    return "❗ Usage: hermes-learning run [limit] [min_samples]"

            result = self._bridge.run_learning_control_cycle(
                limit=limit,
                min_feedback_events=min_samples,
                actor="operator",
                source="hermes-learning-command",
            )
            if not result.get("ok"):
                return f"❌ Manual learning error: {result.get('error', 'unknown')}"

            return (
                "🧠 **Hermes Learning (Manual)**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"Cycle: {result.get('cycle_id', 'unknown')}\n"
                f"Mode: {result.get('mode')}\n"
                f"Decision: {result.get('decision')}\n"
                f"Replay: {result.get('replay', {}).get('evaluated_count', 0)} evaluated / {result.get('replay', {}).get('ready_count', 0)} ready\n"
                f"Health risk: {result.get('health', {}).get('risk_level', 'unknown')} (rollback={result.get('health', {}).get('rollback_trigger', False)})\n"
                f"Tune recommended: {'✅' if result.get('tune', {}).get('apply_recommended') else '⚪'}"
            )

        if action == "ingest":
            if len(args_parts) < 2:
                return "❗ Usage: hermes-learning ingest feedback <task_id> <label> [note] | hermes-learning ingest policy <json> | hermes-learning ingest note <text> [--link <url>] [--file <path>] [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]"

            ingest_kind = args_parts[1].lower()

            if ingest_kind == "feedback":
                if len(args_parts) < 4:
                    return "❗ Usage: hermes-learning ingest feedback <task_id> <label> [note]"
                task_id = args_parts[2]
                label = args_parts[3]
                note = " ".join(args_parts[4:]) if len(args_parts) > 4 else ""
                result = self._bridge.capture_routing_feedback(task_id=task_id, label=label, note=note)
                if not result.get("ok"):
                    return f"❌ Learning ingest error: {result.get('error', 'unknown')}"
                return f"✅ Learning feedback ingested for `{task_id}` → {label}"

            if ingest_kind == "note":
                note_payload = args[len("ingest note"):].strip()
                if not note_payload:
                    return "❗ Usage: hermes-learning ingest note <text> [--link <url>] [--file <path>] [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]"

                explicit_links = re.findall(r"--link\s+(\S+)", note_payload)
                explicit_files = re.findall(r"--file\s+(\S+)", note_payload)

                title_match = re.search(r"--title\s+(.+?)(?=\s--\w+|$)", note_payload)
                title = title_match.group(1).strip() if title_match else ""

                tags_match = re.search(r"--tags\s+(.+?)(?=\s--\w+|$)", note_payload)
                tags_raw = tags_match.group(1).strip() if tags_match else ""
                tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []

                quality_gate = None
                gate_match = re.search(r"--quality-gate\s+([0-9]*\.?[0-9]+)", note_payload)
                if gate_match:
                    try:
                        quality_gate = float(gate_match.group(1))
                    except ValueError:
                        return "❗ Invalid --quality-gate value. Use 0.0 to 1.0"
                    if quality_gate < 0.0 or quality_gate > 1.0:
                        return "❗ Invalid --quality-gate value. Use 0.0 to 1.0"

                force_save = bool(re.search(r"(?:^|\s)--force(?:\s|$)", note_payload))

                note_text = re.sub(r"\s--link\s+\S+", "", note_payload)
                note_text = re.sub(r"\s--file\s+\S+", "", note_text)
                note_text = re.sub(r"\s--title\s+.+?(?=\s--\w+|$)", "", note_text)
                note_text = re.sub(r"\s--tags\s+.+?(?=\s--\w+|$)", "", note_text)
                note_text = re.sub(r"\s--quality-gate\s+[0-9]*\.?[0-9]+", "", note_text)
                note_text = re.sub(r"(?:^|\s)--force(?:\s|$)", " ", note_text)
                note_text = re.sub(r"\s+", " ", note_text).strip()

                extracted_links = self._extract_urls(note_text)
                all_links = []
                for url in explicit_links + extracted_links:
                    if url and url not in all_links:
                        all_links.append(url)

                all_files = []
                for file_path in explicit_files:
                    normalized = file_path.strip().strip('"').strip("'")
                    if normalized and normalized not in all_files:
                        all_files.append(normalized)

                source_notes = []
                for url in all_links:
                    fetched = self._fetch_url_text(url)
                    if fetched:
                        quality = self._score_source_quality(fetched)
                        source_notes.append(
                            {
                                "source": url,
                                "text": fetched,
                                "quality_score": quality.get("score", 0.0),
                                "quality_reason": quality.get("reason", "unknown"),
                            }
                        )

                for file_path in all_files:
                    file_text = self._read_text_file(file_path)
                    if file_text:
                        quality = self._score_source_quality(file_text)
                        source_notes.append(
                            {
                                "source": file_path,
                                "text": file_text,
                                "quality_score": quality.get("score", 0.0),
                                "quality_reason": quality.get("reason", "unknown"),
                            }
                        )

                avg_quality = (
                    sum(float(src.get("quality_score", 0.0)) for src in source_notes) / len(source_notes)
                    if source_notes
                    else 0.0
                )

                if quality_gate is not None and avg_quality < quality_gate and not force_save:
                    return (
                        f"⚠️ Quality gate not met: avg={avg_quality:.0%} < gate={quality_gate:.0%}\n"
                        "Review sources or add stronger evidence first.\n"
                        "Use --force to save anyway."
                    )

                rationale = self._compose_learning_note_rationale(
                    note_text=note_text,
                    sources=source_notes,
                    source_urls=all_links,
                    source_files=all_files,
                    title=title,
                    tags=tags,
                )
                result = self._bridge.propose_policy({}, rationale=rationale)
                if not result.get("ok"):
                    return f"❌ Learning ingest error: {result.get('error', 'unknown')}"
                policy = result.get("policy", {})
                total_sources = len(all_links) + len(all_files)
                return (
                    f"✅ Learning note ingested: {policy.get('policy_id')} (seq {policy.get('policy_sequence')})\n"
                    f"Sources read: {len(source_notes)}/{total_sources}\n"
                    f"Avg quality: {avg_quality:.0%}"
                )

            if ingest_kind == "policy":
                payload_text = args[len("ingest policy"):].strip()
                if not payload_text:
                    return "❗ Usage: hermes-learning ingest policy '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91, \"rationale\": \"...\"}'"
                try:
                    payload = json.loads(payload_text)
                except Exception:
                    return "❗ Usage: hermes-learning ingest policy '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91, \"rationale\": \"...\"}'"
                if not isinstance(payload, dict):
                    return "❗ Usage: hermes-learning ingest policy '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91, \"rationale\": \"...\"}'"
                rationale = str(payload.pop("rationale", "")) if "rationale" in payload else ""
                result = self._bridge.propose_policy(payload, rationale=rationale)
                if not result.get("ok"):
                    return f"❌ Learning ingest error: {result.get('error', 'unknown')}"
                policy = result.get("policy", {})
                return f"✅ Learning policy ingested: {policy.get('policy_id')} (seq {policy.get('policy_sequence')})"

            return "❗ Usage: hermes-learning ingest feedback <task_id> <label> [note] | hermes-learning ingest policy <json> | hermes-learning ingest note <text> [--link <url>] [--file <path>] [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]"

        return "❗ Usage: hermes-learning status|run [limit] [min_samples]|ingest feedback <task_id> <label> [note]|ingest policy <json>|ingest note <text> [--link <url>] [--file <path>] [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]"

    def _extract_urls(self, text: str) -> list[str]:
        """Extract http/https URLs from text."""
        if not text:
            return []
        return re.findall(r"https?://[^\s)\]>\"']+", text)

    def _fetch_url_text(self, url: str, timeout: int = 10, max_chars: int = 4000) -> str:
        """Fetch URL content and return a compact text snapshot."""
        try:
            req = urllib_request.Request(url, headers={"User-Agent": "HermesOS-Learning/1.0"})
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(max_chars * 2).decode("utf-8", errors="ignore")
            clean = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.IGNORECASE)
            clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean[:max_chars]
        except Exception:
            logger.warning(f"[{SKILL_NAME}] Failed to fetch learning source URL: {url}", exc_info=True)
            return ""

    def _read_text_file(self, file_path: str, max_chars: int = 4000) -> str:
        """Read local text/pdf file content safely for learning-note ingestion."""
        try:
            p = Path(file_path).expanduser()
            if not p.exists() or not p.is_file():
                return ""
            if p.suffix.lower() == ".pdf":
                return self._read_pdf_file(str(p), max_chars=max_chars)
            raw = p.read_text(encoding="utf-8", errors="ignore")
            clean = re.sub(r"\s+", " ", raw).strip()
            return clean[:max_chars]
        except Exception:
            logger.warning(f"[{SKILL_NAME}] Failed to read learning source file: {file_path}", exc_info=True)
            return ""

    def _read_pdf_file(self, file_path: str, max_chars: int = 4000) -> str:
        """Best-effort PDF text extraction for learning-note ingestion."""
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            chunks = []
            total = 0
            for page in reader.pages:
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                chunks.append(text)
                total += len(text)
                if total >= max_chars:
                    break
            merged = re.sub(r"\s+", " ", " ".join(chunks)).strip()
            return merged[:max_chars]
        except Exception:
            logger.warning(f"[{SKILL_NAME}] Failed to read PDF source file: {file_path}", exc_info=True)
            return ""

    def _score_source_quality(self, text: str) -> Dict[str, Any]:
        """Heuristic quality score (0..1) for ingested source text."""
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        length = len(compact)
        if length == 0:
            return {"score": 0.0, "reason": "empty"}

        score = min(1.0, length / 800.0)
        if length >= 800:
            reason = "rich"
        elif length >= 250:
            reason = "medium"
        else:
            reason = "short"
        return {"score": round(score, 3), "reason": reason}

    def _compose_learning_note_rationale(
        self,
        note_text: str,
        sources: list[dict],
        source_urls: list[str],
        source_files: list[str],
        title: str = "",
        tags: Optional[list[str]] = None,
    ) -> str:
        """Build policy rationale from operator note + optional linked sources/files."""
        note_compact = re.sub(r"\s+", " ", (note_text or "")).strip()
        note_compact = note_compact[:1500]

        parts = ["manual-learning-note"]
        if title:
            parts.append(f"title: {title}")
        if tags:
            parts.append("tags: " + ", ".join(tags))
        if note_compact:
            parts.append(f"operator_note: {note_compact}")

        if source_urls:
            parts.append("source_urls: " + ", ".join(source_urls[:5]))
        if source_files:
            parts.append("source_files: " + ", ".join(source_files[:5]))

        if sources:
            for src in sources[:5]:
                source = src.get("source", "")
                text = re.sub(r"\s+", " ", src.get("text", "")).strip()[:600]
                score = float(src.get("quality_score", 0.0) or 0.0)
                reason = src.get("quality_reason", "unknown")
                parts.append(f"source_quality[{source}]: {score:.2f} ({reason})")
                parts.append(f"source_summary[{source}]: {text}")

        return " | ".join(parts)[:3500]

    def _handle_hermes_os_command(self, args: str) -> str:
        """Handle hermes-os commands."""
        args = args.strip()
        if not args:
            return self._format_status()
        
        parts = args.split(maxsplit=2)
        subcmd = parts[0]
        rest = args[len(subcmd):].strip() if len(args) > len(subcmd) else ""

        if subcmd == "status":
            return self._format_status()

        elif subcmd == "fleet":
            return self._handle_fleet_command("status")

        elif subcmd == "refresh":
            changed = self._bridge.refresh_mode()
            mode = self._bridge._mode
            return f"🔄 Mode refreshed: {mode}" + (" (changed!)" if changed else "")

        elif subcmd == "feedback":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."
            if not rest:
                return "❗ Usage: hermes-os feedback <task_id> <label> [note]\nLabels: correct, incorrect, should_direct, should_fleet"

            feedback_parts = rest.split(maxsplit=2)
            if len(feedback_parts) < 2:
                return "❗ Usage: hermes-os feedback <task_id> <label> [note]\nLabels: correct, incorrect, should_direct, should_fleet"

            task_id, label = feedback_parts[0], feedback_parts[1]
            note = feedback_parts[2] if len(feedback_parts) >= 3 else ""
            result = self._bridge.capture_routing_feedback(task_id=task_id, label=label, note=note)
            if result.get("ok"):
                return f"✅ Feedback captured for `{task_id}` → {label}"
            return f"❌ Feedback error: {result.get('error', 'unknown error')}"

        elif subcmd == "propose":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            if not rest:
                return "❗ Usage: hermes-os propose <json>"

            try:
                payload = json.loads(rest.strip())
            except Exception:
                return "❗ Usage: hermes-os propose '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91}'"

            if not isinstance(payload, dict):
                return "❗ Usage: hermes-os propose '{\"auto_route_enabled\": true, \"auto_route_threshold\": 0.91}'"

            rationale = str(payload.pop("rationale", "")) if "rationale" in payload else ""
            result = self._bridge.propose_policy(payload, rationale=rationale)
            if not result.get("ok"):
                return f"❌ Policy propose error: {result.get('error', 'unknown')}"
            policy = result.get("policy", {})
            return f"✅ Policy proposed: {policy.get('policy_id')} (seq {policy.get('policy_sequence')})"

        elif subcmd == "policy":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."
            status = self._bridge.get_policy_status()
            if not status.get("ok"):
                return f"❌ {status.get('error', 'unknown error')}"
            policy = status.get("policy_status", {})
            active = policy.get("active", {})
            return ("📚 **Hermes OS Learning Policy**\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Active: {active.get('policy_id', 'unknown')} ({active.get('status', 'unknown')})\n"
                    f"Policy sequence: {active.get('policy_sequence', 'unknown')}\n"
                    f"Source: {active.get('source', 'unknown')}\n"
                    f"Store: {policy.get('store_path', '-')}\n"
                    f"Candidates: {policy.get('candidates', 0)} / Total: {policy.get('total_records', 0)}")

        elif subcmd == "auto-run":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."
            args_parts = rest.split()
            if not args_parts:
                return "❗ Usage: hermes-os auto-run status|set <off|pilot|auto> [reason]|run [limit] [min_samples]|loop [limit] [min_samples] [force]"

            action = args_parts[0].lower()
            if action == "status":
                result = self._bridge.get_auto_run_status()
                if not result.get("ok"):
                    return f"❌ Auto-run status error: {result.get('error', 'unknown')}"
                state = result.get("state", {}) or {}
                auto_run_status = result.get("latest_cycle", {}) or {}
                return (
                    "⚙️ **Hermes OS Auto-Run**\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Mode: {state.get('mode', 'off')}\n"
                    f"Canary: {state.get('canary_percent', 0):.2%}\n"
                    f"Cooldown: {state.get('cooldown_minutes', 0)} minutes\n"
                    f"Next cycle in: {result.get('remaining_cooldown_seconds', 0)} seconds\n"
                    f"Next cycle at: {result.get('next_cycle_at') or 'N/A'}\n"
                    f"Kill-switch: {'ON' if state.get('kill_switch', False) else 'OFF'}\n"
                    f"Last cycle: {state.get('last_cycle_id', 'never')} ({state.get('last_cycle_mode', '-')})\n"
                    f"Last decision: {state.get('last_cycle_decision', '-') }\n"
                    f"Last at: {state.get('last_cycle_at', '-') }\n"
                    f"Max daily change: {state.get('max_daily_change_rate', 0):.2%}\n"
                    f"Decision: {auto_run_status.get('decision', 'waiting')}"
                )
            if action == "set":
                if len(args_parts) < 2:
                    return "❗ Usage: hermes-os auto-run set <off|pilot|auto> [reason]"
                mode = args_parts[1]
                if mode.lower() != "off":
                    return (
                        "🧠 Manual learning only: auto modes are disabled.\n"
                        "Use `hermes-learning run [limit] [min_samples]` for explicit operator-triggered learning."
                    )
                reason = " ".join(args_parts[2:]) if len(args_parts) > 2 else "manual update"
                result = self._bridge.set_auto_run_mode(mode=mode, actor="operator", reason=reason)
                if not result.get("ok"):
                    return (
                        "❌ Invalid auto-run mode: "
                        f"{result.get('error')} "
                        f"Valid modes: {', '.join(result.get('valid_modes', []))}"
                    )
                return (
                    "✅ Auto-run mode updated\n"
                    f"Mode: {result.get('previous_mode', 'off')} -> {result.get('mode', 'off')}\n"
                    f"Updated by: {result.get('state', {}).get('updated_by', 'operator')}"
                )
            if action == "loop":
                return (
                    "🧠 Manual learning only: scheduler loop is disabled.\n"
                    "Use `hermes-learning run [limit] [min_samples]` for explicit operator-triggered learning."
                )
            if action == "run":
                return (
                    "🧠 Manual learning only: `hermes-os auto-run run` is deprecated.\n"
                    "Use `hermes-learning run [limit] [min_samples]` instead."
                )
            return "❗ Usage: hermes-os auto-run status|set <off|pilot|auto> [reason]|run [limit] [min_samples]|loop [limit] [min_samples] [force]"

        elif subcmd == "apply":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            if not rest:
                return "❗ Usage: hermes-os apply <policy_id> [reason]"
            parts = rest.split(maxsplit=1)
            policy_id = parts[0]
            reason = parts[1] if len(parts) > 1 else "manual-approval"

            readiness = self._bridge.evaluate_policy_readiness(policy_id=policy_id, min_feedback_events=20)
            if not readiness.get("ok"):
                reason_text = ", ".join(readiness.get("reason_codes", []) or [readiness.get("error", "unknown")])
                return f"❌ Policy apply blocked: {reason_text}"

            readiness_report = readiness.get("policy_report") or {}
            if not readiness_report.get("acceptance_passed"):
                lines = self._format_readiness_report(policy_id=policy_id, readiness=readiness)
                lines += "\n\n🚫 Apply blocked: all checklist items must be ✅ before operational apply."
                return lines

            result = self._bridge.apply_policy(policy_id=policy_id, reason=reason)
            if not result.get("ok"):
                return f"❌ Policy apply error: {result.get('error', 'unknown')}"
            return f"{self._format_readiness_report(policy_id=policy_id, readiness=readiness)}\n\n✅ Policy applied: {policy_id}"

        elif subcmd == "readiness":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            parts = rest.split()
            if not parts:
                return "❗ Usage: hermes-os readiness <policy_id> [min_samples]"

            policy_id = parts[0]
            min_samples = 20
            if len(parts) > 1:
                try:
                    min_samples = max(1, int(parts[1]))
                except ValueError:
                    return "❗ Usage: hermes-os readiness <policy_id> [min_samples]"

            result = self._bridge.evaluate_policy_readiness(
                policy_id,
                min_feedback_events=min_samples,
            )
            if not result.get("ok"):
                reason = ", ".join(result.get("reason_codes", []) or [result.get("error", "unknown")])
                return f"❌ Policy readiness error: {reason}"
            return self._format_readiness_report(policy_id=policy_id, readiness=result)

        elif subcmd == "replay":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            args_parts = rest.split()
            limit = None
            min_samples = 20
            if args_parts:
                try:
                    if len(args_parts) >= 1:
                        limit = int(args_parts[0])
                    if len(args_parts) >= 2:
                        min_samples = max(1, int(args_parts[1]))
                except ValueError:
                    return "❗ Usage: hermes-os replay [limit] [min_samples]"

            result = self._bridge.evaluate_learning_policy_candidates(
                limit=limit,
                min_feedback_events=min_samples,
            )
            if not result.get("ok"):
                return f"❌ Replay evaluation error: {result.get('error', 'unknown')}"

            lines = [
                "🧪 **Hermes OS Replay Evaluation**",
                "━━━━━━━━━━━━━━━━━━━━━",
                f"Evaluated: {result.get('evaluated_count', 0)}",
                f"Ready: {result.get('ready_count', 0)} / Blocked: {result.get('blocked_count', 0)}",
                "",
            ]

            for row in result.get("evaluations", [])[:8]:
                status = "✅" if row.get("ready") else "⚠️"
                reasons = ", ".join(row.get("reason_codes", []))
                lines.append(
                    f"{status} {row.get('policy_id', 'unknown')} "
                    f"({row.get('observed_feedback_total', 0)}/{row.get('required_feedback_total', min_samples)})"
                )
                if reasons:
                    lines.append(f"  • {reasons}")
            if not result.get("evaluations"):
                lines.append("No candidate policies to evaluate.")
            return "\n".join(lines)

        elif subcmd == "health":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            args_parts = rest.split()
            min_samples = 20
            if args_parts:
                try:
                    min_samples = max(1, int(args_parts[0]))
                except ValueError:
                    return "❗ Usage: hermes-os health [min_samples]"

            status = self._bridge.assess_active_policy_health(min_feedback_events=min_samples)
            if not status.get("ok"):
                return f"⚠️ Active policy health: {status.get('error', 'insufficient_feedback')}"

            return (
                "🛡️ **Hermes OS Active Policy Health**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"Rollback trigger: {'🚨' if status.get('rollback_trigger') else '✅'}\n"
                f"Risk level: {status.get('risk_level', 'unknown')}\n"
                f"Manual override rate: {status.get('manual_override_rate', 0):.2%}\n"
                f"False positive rate: {status.get('false_positive_rate', 0):.2%}\n"
                f"Notes: {', '.join(status.get('notes', []) or ['OK'])}"
            )

        elif subcmd == "tune":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            args_parts = rest.split()
            min_samples = 20
            if args_parts:
                try:
                    min_samples = max(1, int(args_parts[0]))
                except ValueError:
                    return "❗ Usage: hermes-os tune [min_samples]"

            result = self._bridge.propose_guarded_auto_tune(min_feedback_events=min_samples)
            if not result.get("ok"):
                return f"❌ Guarded tune unavailable: {result.get('error', 'unknown')}"

            if result.get("rollback_trigger"):
                return "⚠️ Guarded tune blocked due to rollback risk: " + ", ".join(result.get("reason_codes", []))

            lines = [
                "🧠 **Hermes OS Guarded Tuning**",
                "━━━━━━━━━━━━━━━━━━━━━",
                f"Apply recommended: {'true' if result.get('apply_recommended') else 'false'}",
            ]
            for code in result.get("reason_codes", []):
                lines.append(f"- {code}")
            for item in result.get("suggestions", []):
                lines.append(
                    f"• {item.get('type')}: {item.get('from')} -> {item.get('to')} ({item.get('rationale')})"
                )
            if result.get("notes"):
                lines.extend([f"• {note}" for note in result.get("notes", [])])
            if not result.get("suggestions") and not result.get("reason_codes"):
                lines.append("No tuning signal available at this time.")
            return "\n".join(lines)


        elif subcmd == "metrics":
            if not self.is_active():
                return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."

            limit = None
            if rest:
                try:
                    limit = max(1, int(rest.strip()))
                except ValueError:
                    return "❗ Usage: hermes-os metrics [limit]"

            metrics = self._bridge.get_feedback_metrics(limit=limit)
            if not metrics.get("ok"):
                return f"❌ {metrics.get('error', 'unknown error')}"

            route_mix = metrics.get("route_mix", {})
            labels = metrics.get("feedback", {}).get("labels", {})
            fp = metrics.get("feedback", {}).get("false_positive", {})
            lines = [
                "📊 **Hermes OS Routing Feedback Metrics**",
                "━━━━━━━━━━━━━━━━━━━━━",
                f"routing_total: {metrics.get('routing_total', 0)}",
                f"feedback_total: {metrics.get('feedback_total', 0)}",
                f"manual_override_rate: {metrics.get('manual_override_rate', 0):.2%}",
                "",
                "**Route Mix:**",
                f"  direct: {route_mix.get('direct', 0)}",
                f"  fleet: {route_mix.get('fleet', 0)}",
                f"  direct_with_suggestion: {route_mix.get('direct_with_suggestion', 0)}",
                f"  unknown: {route_mix.get('unknown', 0)}",
                "",
                "**Feedback Labels:**",
                f"  correct: {labels.get('correct', 0)}",
                f"  incorrect: {labels.get('incorrect', 0)}",
                f"  should_direct: {labels.get('should_direct', 0)}",
                f"  should_fleet: {labels.get('should_fleet', 0)}",
                "",
                "**False Positive Signals:**",
                f"  should_direct: {fp.get('should_direct', {}).get('count', 0)} (rate {fp.get('should_direct', {}).get('rate', 0):.2%})",
                f"  should_fleet: {fp.get('should_fleet', {}).get('count', 0)} (rate {fp.get('should_fleet', {}).get('rate', 0):.2%})",
                f"  total: {fp.get('total', 0)} (rate {fp.get('rate', 0):.2%})",
            ]
            return "\n".join(lines)

        else:
            return """🛰️ **Hermes OS Commands**
━━━━━━━━━━━━━━━━━━━━━

hermes-os           - Show OS status
hermes-os status    - Detailed status
hermes-os fleet     - Fleet health
hermes-os feedback  - Capture routing feedback
hermes-os metrics   - Show feedback metrics
hermes-os policy    - Show learning policy status
hermes-os propose   - Propose policy candidate from JSON payload
hermes-os apply     - Apply policy id
hermes-os readiness - Evaluate policy readiness
hermes-os replay    - Evaluate candidate policies with offline replay
hermes-os health    - Assess active policy rollback risk
hermes-os tune      - Guarded auto-tuning recommendation
hermes-os auto-run  - Show auto-run status, set mode, run cycle, or run loop gate
hermes-os refresh   - Refresh mode check

fleet "task"        - Route task to Fleet
fleet plan "task"   - Dry run
fleet run "task"    - Execute task
hermes-learning     - Manual learning controls (status/run/ingest note+links+files+title+tags+quality)

Hermes OS auto-routes tasks when active."""

    
    def _format_readiness_report(self, policy_id: str, readiness: Dict[str, Any]) -> str:
        """Render a readable readiness review card for policy candidates."""
        policy_report = readiness.get("policy_report") or {}
        acceptance = bool(policy_report.get("acceptance_passed", False))
        reason_codes = readiness.get("reason_codes", []) or []
        notes = readiness.get("notes", []) or []
        replay = policy_report.get("replay", {}) or {}
        signals = policy_report.get("signals", {}) or {}
        observed = int(policy_report.get("observed_feedback_total", readiness.get("observed_feedback_total", 0)) or 0)
        required = int(policy_report.get("required_feedback_total", readiness.get("required_feedback_total", 0)) or 0)
        failed_signals = policy_report.get("failed_signals", []) or []

        reason_explanations = {
            "insufficient_feedback_samples": "ตัวอย่าง feedback ยังไม่ถึง threshold ที่ตั้งใจไว้; ควรรวบรวมอีกก่อนประเมินพร้อมกัน",
            "policy_not_ready_for_readiness": "policy นี้ยังไม่ใช่สถานะ `candidate`; readiness ใช้ได้เฉพาะ candidate เท่านั้น",
            "too_many_should_direct_false_positives": "พบสัญญาณ `should_direct` false positive สูงเกินเกณฑ์; เสี่ยง under-route Fleet",
            "too_many_should_fleet_false_positives": "พบสัญญาณ `should_fleet` false positive สูง; เสี่ยง over-route Fleet",
            "too_many_false_positive_events": "จำนวน false-positive รวมสูงเกิน safe limit",
            "candidate_threshold_invalid": "ค่า threshold candidate ไม่ถูกต้อง/อ่านไม่ออกทางระบบ",
            "candidate_threshold_below_guardrail": "Candidate threshold ต่ำกว่า guardrail ล่างที่อนุญาต",
            "candidate_threshold_delta_exceeds_guardrail": "การเปลี่ยน threshold จาก active มากเกินเพดาน guardrail",
            "offline_replay_no_events": "ยังไม่มี routing history สำหรับ offline replay",
            "offline_replay_insufficient_history": "ข้อมูล replay ไม่พอสำหรับการประเมิน route drift แบบปลอดภัย",
            "offline_replay_too_many_route_changes": "ผล replay มี route flip สูง เสี่ยงเสถียรภาพการรันต่ำ",
            "offline_replay_recent_drift_risk": "รีเพลย์ช่วงล่าสุดมี drift สูงกว่าเกณฑ์ความนิ่งที่ยอมรับได้",
            "offline_replay_confidence_low": "sample replay ยังน้อยเกินไป/ความเชื่อมั่นสถิติยังไม่พอ",
            "offline_replay_seasonal_shift_risk": "มีสัญญาณขยับตามฤดูกาลใน behavior เสี่ยง drift",
            "offline_replay_route_sparsity_risk": "บาง route mismatch เกิดจาก sample น้อยเกินไป (under-sampled)",
            "policy_simulation_pending": "ยังไม่ได้ทำ replay simulation แล้วจึงยังประเมิน readiness ไม่ได้",
            "policy_simulation_passed": "ผ่าน replay simulation ตามกติกา safety ที่ตั้งไว้",
            "policy_state": "นโยบายมีสถานะไม่พร้อมประเมิน readiness หรือถูกปิดใช้งาน",
            "candidate_threshold": "ข้อมูล threshold ใน candidate ไม่ครบหรือไม่สามารถตีความได้",
        }

        def _pct(value: Any) -> str:
            try:
                return f"{float(value) * 100:.2f}%"
            except (TypeError, ValueError):
                return "0.00%"

        def _flag(value: bool) -> str:
            return "✅" if value else "⚠️"

        lines = [
            "🧾 **Hermes OS Policy Readiness**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"Policy: {policy_id}",
            f"Acceptance: {_flag(acceptance)} {'PASS' if acceptance else 'REVIEW_REQUIRED'}",
            f"Feedback sample: {observed} / {required}",
            "",
            "**Signals:**",
        ]

        if signals:
            for signal_name in sorted(signals.keys()):
                signal = signals.get(signal_name, {})
                passed = bool(signal.get("passed", False))
                blockers = ", ".join(signal.get("blockers", []))
                label = signal_name.replace("_", " ").title()
                line = f"  {_flag(passed)} {label}"
                if blockers:
                    line += f" ({blockers})"
                lines.append(line)
        else:
            lines.append("  (no signal breakdown available)")

        lines.extend([
            "",
            "**Offline replay:**",
            f"  Simulated events: {int(replay.get('simulated_events', 0) or 0)}",
            f"  Overall route flip: {_pct(replay.get('route_flip_rate', 0.0))}",
            f"  Upper bound flip: {_pct(replay.get('route_flip_rate_upper_bound', 0.0))}",
            f"  Recent route flip: {_pct(replay.get('recent_route_flip_rate', 0.0))}",
            f"  Seasonal flip delta: {_pct(replay.get('seasonal_flip_delta', 0.0))}",
        ])

        if replay.get("sparse_mismatch_routes"):
            lines.append(f"  Sparse mismatch routes: {', '.join(replay.get('sparse_mismatch_routes', []))}")

        if reason_codes:
            lines.append("")
            lines.append("**Reason insights:**")
            for reason_code in reason_codes:
                explanation = reason_explanations.get(reason_code, "รหัสเตือนนี้ยังไม่มีคำอธิบายในระบบ ให้ตรวจ notes และสรุป signal ต่อไปนี้")
                lines.append(f"  • {reason_code}: {explanation}")
        if failed_signals:
            lines.append(f"**Failed signals:** {', '.join(failed_signals)}")

        if notes:
            lines.append("**Notes:**")
            for note in notes[:4]:
                lines.append(f"  • {note}")

        if acceptance:
            lines.append("\n✅ Ready to request operational apply (manual approval only).")
        else:
            lines.append("\n⚠️ Not ready for apply. Please satisfy all signal gates first.")

        lines.extend(self._format_apply_checklist(policy_report))

        return "\n".join(lines)

    def _format_apply_checklist(self, policy_report: Dict[str, Any]) -> list[str]:
        """Render a standardized apply-readiness checklist."""
        policy_report = policy_report or {}
        lines = ["", "**Apply approval checklist:**"]
        signals = policy_report.get("signals", {}) or {}

        if not signals:
            lines.append("  (No signal data available)")
            return lines

        for signal_name in sorted(signals.keys()):
            signal = signals.get(signal_name, {})
            passed = bool(signal.get("passed", False))
            blockers = ", ".join(signal.get("blockers", []) or [])
            label = signal_name.replace("_", " ").title()
            line = f"  {'✅' if passed else '⚠️'} {label}"
            if blockers:
                line += f" ({blockers})"
            lines.append(line)

        return lines

    def _handle_fleet_command(self, args: str) -> str:
        """Handle fleet commands."""
        if not args or args.strip() in ["", "status"]:
            # Show fleet status
            try:
                from integrations.telegram_bridge import handle_hermes_os_command
                return handle_hermes_os_command("fleet", "")
            except Exception as e:
                return f"❌ Error: {str(e)[:200]}"
        
        # Parse task
        parts = args.strip().split(maxsplit=1)
        if len(parts) == 0:
            return "Usage: fleet [plan|run] \"your task\""
        
        subcmd = parts[0]
        task = parts[1] if len(parts) > 1 else ""
        
        if subcmd in ["plan", "run"]:
            if not task:
                return f"Usage: fleet {subcmd} \"your task\""
            
            dry_run = (subcmd == "plan")
            return self._execute_task(task, dry_run=dry_run, manual_override="fleet")
        
        # Default: treat entire args as task
        return self._execute_task(args.strip(), dry_run=False, manual_override="fleet")

    def _execute_task(self, task: str, dry_run: bool = False, manual_override: Optional[str] = None) -> str:
        """Execute task through Hermes OS."""
        if not self.is_active():
            return "🔴 Hermes OS mode is OFF"
        
        context: Dict[str, Any] = {
            "platform": "telegram",
            "dry_run": dry_run,
            "manual_override": manual_override,
            "source": "hermes_os_fleet_command",
            "raw_task": task,
        }

        try:
            result = self._bridge.process_message(
                task,
                boss_id="telegram_user",
                boss_name="Boss",
                chat_id=None,
                context=context,
            )
            
            if result.get("handled"):
                return result.get("response", "No response")
            else:
                return "⚠️ Task not handled by Hermes OS"
                
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return f"❌ Error: {str(e)[:500]}"

    def _format_status(self) -> str:
        """Format Hermes OS status for display."""
        if not self.is_active():
            return "🔴 Hermes OS mode is OFF\n\nRun `hermes-os` in terminal to activate."
        
        try:
            status = self._bridge._os.status()
            
            lines = [
                "🛰️ **Hermes OS Status**",
                "━━━━━━━━━━━━━━━━━━━━━",
                "",
                f"Mode: {status.get('mode', 'unknown')}",
                f"Active: {'🟢 Yes' if status.get('active') else '🔴 No'}",
                f"Version: {status.get('version', 'unknown')}",
                "",
                "**Components:**",
            ]
            
            for name, ready in status.get('components', {}).items():
                lines.append(f"  {'✅' if ready else '❌'} {name}")
            
            if fleet := status.get('fleet'):
                lines.append("")
                lines.append(f"**Fleet**: {fleet['main_agents']}M/{fleet['sub_agents']}S agents")
            
            phase3 = status.get('phase3', {})
            lines.append("")
            lines.append("**Phase-3:**")
            lines.append(f"  Analyze-Only: {'🟢' if phase3.get('analyze_only') else '🔴'}")
            lines.append(f"  Auto-Route: {'🟢 ON' if phase3.get('auto_route_enabled') else '🔴 OFF'}")
            lines.append(f"  Auto-Route Threshold: {phase3.get('auto_route_threshold')}")

            auto_run = status.get('auto_run', {})
            lines.append("")
            lines.append("**Auto-Run:**")
            lines.append(f"  Mode: {auto_run.get('mode', 'off')}")
            lines.append(f"  State: {auto_run.get('state', {}).get('kill_switch', False)}")
            lines.append(f"  Canary: {auto_run.get('state', {}).get('canary_percent', 0):.2%}")
            lines.append(f"  Cooldown: {auto_run.get('state', {}).get('cooldown_minutes', 0)} min")
            lines.append(f"  Max Daily Change: {auto_run.get('state', {}).get('max_daily_change_rate', 0):.2%}")

            policy_state = status.get('policy', {})
            lines.append("")
            lines.append("**Learning Policy:**")
            lines.append(f"  Active: {policy_state.get('active_id', 'unknown')} ({policy_state.get('status', 'unknown')})")
            lines.append(f"  Policy Sequence: {policy_state.get('active_sequence', 'unknown')}")
            lines.append(f"  Store: {policy_state.get('policy_store_path', '-')}")
            lines.append(f"  Ledger: {policy_state.get('policy_ledger_path', '-')}")

            policy_id = self._resolve_latest_candidate_policy_id(policy_state)
            if policy_id:
                lines.append("")
                lines.append("**Latest Candidate Readiness Summary:**")
                readiness = self._bridge.evaluate_policy_readiness(policy_id=policy_id, min_feedback_events=20)
                if readiness.get("ok"):
                    lines.extend(self._render_policy_report_summary(policy_id=policy_id, readiness=readiness))
                else:
                    reason = ", ".join(readiness.get("reason_codes", []) or [readiness.get("error", "unknown")])
                    lines.append(f"⚠️ Policy-readiness unavailable: {reason}")
            else:
                lines.append("")
                lines.append("**Latest Candidate Readiness Summary:**")
                lines.append("  No pending candidate policy found.")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Error getting status: {str(e)[:200]}"

    def _resolve_latest_candidate_policy_id(self, policy_state: Dict[str, Any]) -> Optional[str]:
        """Resolve latest pending candidate policy id for report preview in status card."""
        if not policy_state:
            return None
        if int(policy_state.get("policy_candidates", 0) or 0) <= 0 and int(policy_state.get("candidates", 0) or 0) <= 0:
            return None

        policies = self._bridge._os.get_learning_policies(include_inactive=True)
        if not policies:
            return None

        candidates = [record for record in policies if str(record.get("status", "")) == "candidate"]
        if not candidates:
            return None

        latest_candidate = candidates[-1]
        return latest_candidate.get("policy_id")

    def _render_policy_report_summary(self, policy_id: str, readiness: Dict[str, Any]) -> list[str]:
        """Render compact policy report summary for status card."""
        report = readiness.get("policy_report") or {}
        lines: list[str] = []
        observed = int(
            report.get("observed_feedback_total", readiness.get("observed_feedback_total", 0) or 0)
        )
        required = int(
            report.get("required_feedback_total", readiness.get("required_feedback_total", 0) or 0)
        )
        acceptance = bool(report.get("acceptance_passed", False))
        failed_signals = report.get("failed_signals", []) or []

        lines.append(f"  Policy: {policy_id}")
        lines.append(f"  Acceptance: {'✅ PASS' if acceptance else '⚠️ REVIEW_REQUIRED'}")
        lines.append(f"  Feedback sample: {observed} / {required}")

        if failed_signals:
            lines.append(f"  Failed signals: {', '.join(failed_signals)}")

        lines.extend(self._format_apply_checklist(report))
        return lines

    def _handle_fleet_command(self, args: str) -> str:
        """Handle fleet commands."""
        if not args or args.strip() in ["", "status"]:
            # Show fleet status
            try:
                from integrations.telegram_bridge import handle_hermes_os_command
                return handle_hermes_os_command("fleet", "")
            except Exception as e:
                return f"❌ Error: {str(e)[:200]}"

        # Parse task
        parts = args.strip().split(maxsplit=1)
        if len(parts) == 0:
            return "Usage: fleet [plan|run] \"your task\""
# Hermes Skill Interface Functions
# These are called by Hermes when loading the skill

def load_skill(hermes_context=None) -> HermesOSSkill:
    """
    Load the skill. Called by Hermes on startup.
    
    Args:
        hermes_context: Hermes context object
        
    Returns:
        Initialized skill instance
    """
    skill = HermesOSSkill(hermes_context)
    skill.initialize()
    return skill


def get_commands() -> Dict[str, str]:
    """
    Get available commands. Called by Hermes for command discovery.
    
    Returns:
        Dict of command -> description
    """
    return {
        "hermes-os": "Hermes OS status and management",
        "hermes-learning": "Manual learning controls (operator-triggered only)",
        "fleet": "Route tasks to Enterprise Agent Fleet",
    }


def get_help() -> str:
    """Get help text for the skill."""
    return """🛰️ Hermes OS Integration

Auto-routes tasks to Enterprise Agent Fleet when in hermes_os mode.

Commands:
  hermes-os           Show OS status
  hermes-os fleet     Fleet health
  hermes-learning     Manual learning control (operator-triggered: status/run/ingest note+links+files+title+tags+quality)
hermes-os feedback  Capture feedback for routed task
hermes-os metrics   Show routing feedback metrics
hermes-os policy    Show learning policy status
hermes-os propose   Propose learning policy candidate
hermes-os apply     Apply policy id
hermes-os readiness Evaluate policy readiness
  fleet "task"        Route task to Fleet
  fleet plan "task"   Dry run

Boss never needs to know if Hermes or Fleet handles the task.
"""


# Backwards compatibility interface
_skills = {}


def skill_register(skill_name: str, hermes_context=None):
    """Register this skill with Hermes."""
    if skill_name == SKILL_NAME:
        _skills[skill_name] = load_skill(hermes_context)
        return _skills[skill_name]
    return None


def skill_call(skill_name: str, method: str, *args, **kwargs):
    """Call a method on the skill."""
    if skill_name not in _skills:
        return None
    
    skill = _skills[skill_name]
    if hasattr(skill, method):
        return getattr(skill, method)(*args, **kwargs)
    return None


# Main entry point for Hermes
if __name__ == "__main__":
    # Test the skill
    print(f"🛰️ Testing {SKILL_NAME} v{SKILL_VERSION}...")
    
    skill = load_skill()
    
    if skill.is_active():
        print("✅ Hermes OS is active")
        print("\nStatus:")
        print(skill._format_status())
    else:
        print("🔴 Hermes OS mode is OFF")
        print("\nRun `hermes-os` to activate")
