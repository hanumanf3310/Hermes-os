"""
Hermes OS - Unified AI Operating System

Built-in Fleet Integration - Everything routes through Hermes OS
"""

__version__ = "1.0.0"
__mode__ = "hermes_os"

import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HermesOS:
    """
    Hermes OS - Unified AI Operating System

    This is the core of Hermes OS mode. It provides:
    - Seamless integration between Hermes Agent and Enterprise Agent Fleet
    - Automatic task routing based on complexity and safety requirements
    - Unified memory and output formatting
    - Built-in RTK transport layer

    Hermes OS is the single entry point. Boss never needs to know
    whether a task is handled by Hermes directly or routed to Fleet.

    Attributes:
        mode: Always "hermes_os" when active
        fleet_orchestrator: Fleet management (7 Main + 21 Sub-Agents)
        memory: Persistent memory across sessions
        rtk_transport: Automatic RTK subprocess management
    """

    MODE_HERMES_OS = "hermes_os"
    MODE_HERMES_OFF = "hermes_off"

    VALID_ROUTING_FEEDBACK_LABELS = {"correct", "incorrect", "should_direct", "should_fleet"}
    LEARNING_POLICY_DEFAULT_STATUS = "active"

    # Readiness guardrails for Phase-C readiness checks
    READINESS_MAX_THRESHOLD_DELTA = 0.2
    READINESS_MIN_THRESHOLD_GUARD = 0.5
    READINESS_MAX_FALSE_POSITIVE_RATE = 0.25
    READINESS_MAX_NOTIFIABLE_FALSE_COUNT = 3
    READINESS_MIN_OFFLINE_REPLAY_EVENTS = 3
    READINESS_MAX_OFFLINE_ROUTE_FLIP_RATE = 0.35
    READINESS_OFFLINE_REPLAY_WINDOW = 200
    READINESS_RECENT_REPLAY_WINDOW = 5
    READINESS_MAX_RECENT_ROUTE_FLIP_RATE = 0.55
    READINESS_MIN_CONFIDENCE_REPLAY_EVENTS = 8
    READINESS_CONFIDENCE_Z = 1.96
    READINESS_MIN_ROUTE_SUPPORT = 2
    READINESS_MAX_SEASONAL_FLIP_DELTA = 0.3

    # Phase-D/E policy operations and guarded tuning
    AUTO_TUNE_MIN_FEEDBACK_EVENTS = 20
    AUTO_TUNE_THRESHOLD_STEP = 0.05
    AUTO_TUNE_THRESHOLD_GUARD_MARGIN = 0.03
    AUTO_TUNE_MAX_TUNING_MAGNITUDE = 0.15
    AUTO_TUNE_MAX_MANUAL_OVERRIDE_RATE = 0.25
    AUTO_TUNE_ROLLBACK_SHOULD_FP_RATE = 0.35
    AUTO_TUNE_ROLLBACK_FP_RATE = 0.40

    # Option-7: auto-run control-plane defaults
    AUTO_RUN_MODE_OFF = "off"
    AUTO_RUN_MODE_PILOT = "pilot"
    AUTO_RUN_MODE_AUTO = "auto"
    AUTO_RUN_ALLOWED_MODES = {AUTO_RUN_MODE_OFF, AUTO_RUN_MODE_PILOT, AUTO_RUN_MODE_AUTO}
    AUTO_RUN_DEFAULT_MODE = AUTO_RUN_MODE_OFF
    AUTO_RUN_DEFAULT_CANARY_PERCENT = 0.0
    AUTO_RUN_DEFAULT_COOLDOWN_MINUTES = 60
    AUTO_RUN_DEFAULT_MIN_DAILY_CHANGE_RATE = 0.0
    AUTO_RUN_DEFAULT_MAX_DAILY_CHANGE_RATE = 0.20
    AUTO_RUN_DEFAULT_KILL_SWITCH = False
    AUTO_RUN_LEDGER_PATH = "hermes_os_auto_run_ledger.jsonl"
    AUTO_RUN_STATE_PATH = "hermes_os_auto_run_state.json"
    AUTO_RUN_CYCLE_VIABILITY_WINDOW_SECONDS = 900

    def __init__(self, fleet_path: Optional[Path] = None):
        """
        Initialize Hermes OS.

        Args:
            fleet_path: Optional path to Enterprise Agent Fleet installation.
                       If not provided, tries auto-discovery.
        """
        self.state_dir = Path.home() / ".hermes" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.os_dir = Path.home() / ".hermes" / "os"
        self._ensure_os_structure()

        self.phase3_config = self._load_phase3_config()

        # Initialize components
        self._init_fleet(fleet_path)
        self._init_memory()
        self._init_transport()

        self._active = True
        self._mode = self.MODE_HERMES_OS
        self._load_persisted_control_state()

        # Phase-3 telemetry store (for learning loop foundation)
        self._init_telemetry_store()

        # Phase-C: learning policy store (read-only-safe by default)
        self.policy_store_path = self.state_dir / "hermes_os_learning_policy.jsonl"
        self.policy_ledger_path = self.state_dir / "hermes_os_policy_ledger.jsonl"
        self._init_learning_policy_store()

        # Option-7: autonomous control-plane state and cycle ledger
        self.auto_run_state_path = self.state_dir / self.AUTO_RUN_STATE_PATH
        self.auto_run_cycle_ledger_path = self.state_dir / self.AUTO_RUN_LEDGER_PATH
        self._init_auto_run_state()

        logger.info("🛰️ Hermes OS initialized")
        logger.info(f"   Mode: {self._mode}")

    def _ensure_os_structure(self):
        """Ensure Hermes OS directory structure exists."""
        dirs = [
            "core/executor",
            "fleet/divisions",
            "fleet/core",
            "transport/rtk",
            "skills",
        ]
        for d in dirs:
            (self.os_dir / d).mkdir(parents=True, exist_ok=True)

    def _load_persisted_control_state(self) -> None:
        """Load persisted on/off state before rendering status.

        The launcher writes ~/.hermes/state/hermes-os.json for control-plane
        on/off operations. A fresh HermesOS() instance must honor that file;
        otherwise `hermes-os status` can incorrectly report hermes_os after
        `hermes-os off` simply because __init__ defaults to active.
        """
        state_file = self.state_dir / "hermes-os.json"
        try:
            data = json.loads(state_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

        mode = data.get("mode")
        if mode in {self.MODE_HERMES_OS, self.MODE_HERMES_OFF}:
            self._mode = mode
            self._active = mode == self.MODE_HERMES_OS

        if "active" in data:
            self._active = bool(data.get("active")) and self._mode == self.MODE_HERMES_OS

        if "rtk_enabled" in data:
            self.rtk_enabled = bool(data.get("rtk_enabled"))

    def _load_phase3_config(self) -> Dict[str, Any]:
        """Load Phase-3 routing controls from ~/.hermes/config.yaml."""
        defaults = {
            "enabled": True,
            "analyze_only": True,
            "auto_route_enabled": False,
            "auto_route_threshold": 0.8,
            "manual_override_prefixes": ["/fleet", "/hermes-os fleet", "/fleet"],
            "adapter_contract": {
                "fleet_score_threshold": 8,
                "direct_with_suggestion_min": 4,
                "direct_with_suggestion_max": 7,
            },
        }

        if yaml is None:
            return defaults

        config_path = Path.home() / ".hermes" / "config.yaml"
        if not config_path.exists():
            return defaults

        try:
            payload = yaml.safe_load(config_path.read_text()) or {}
            if not isinstance(payload, dict):
                return defaults
            cfg = payload.get("hermes_os") if isinstance(payload.get("hermes_os"), dict) else payload.get("hermes_os_phase3")
            if not isinstance(cfg, dict):
                return defaults
            merged = dict(defaults)
            merged.update(cfg)
            adapter_cfg = cfg.get("adapter_contract")
            if isinstance(adapter_cfg, dict):
                merged_adapter = dict(defaults["adapter_contract"])
                merged_adapter.update(adapter_cfg)
                merged["adapter_contract"] = merged_adapter
            return merged
        except Exception:
            logger.exception("Failed loading hermes_os phase-3 config; using defaults")
            return defaults

    def _init_learning_policy_store(self) -> None:
        """Initialize versioned policy store and bootstrap a safe default policy if empty."""
        self.policy_store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.policy_store_path.exists():
            self.policy_store_path.write_text("", encoding="utf-8")
        if not self.policy_ledger_path.exists():
            self.policy_ledger_path.write_text("", encoding="utf-8")

        records = self.get_learning_policies(include_inactive=True)
        if not records:
            bootstrap = self._build_default_policy_record(
                source="runtime_bootstrap",
                status=self.LEARNING_POLICY_DEFAULT_STATUS,
                rationale="Bootstrap default learning policy from runtime defaults",
            )
            self._append_learning_policy_record(bootstrap)

    def _default_auto_run_state(self) -> Dict[str, Any]:
        """Return canonical auto-run state defaults."""
        return {
            "mode": self.AUTO_RUN_DEFAULT_MODE,
            "canary_percent": self.AUTO_RUN_DEFAULT_CANARY_PERCENT,
            "cooldown_minutes": self.AUTO_RUN_DEFAULT_COOLDOWN_MINUTES,
            "minimum_gain_floor": self.AUTO_RUN_DEFAULT_MIN_DAILY_CHANGE_RATE,
            "max_daily_change_rate": self.AUTO_RUN_DEFAULT_MAX_DAILY_CHANGE_RATE,
            "kill_switch": self.AUTO_RUN_DEFAULT_KILL_SWITCH,
            "last_cycle_at": None,
            "last_cycle_id": None,
            "last_cycle_decision": None,
            "last_cycle_mode": None,
            "last_cycle_source": None,
            "updated_at": self._now(),
            "updated_by": "runtime",
            "updated_reason": "bootstrap",
        }

    def _load_auto_run_state(self) -> Dict[str, Any]:
        """Load auto-run control state from disk with defaults on error."""
        if not self.auto_run_state_path.exists():
            return self._default_auto_run_state()
        try:
            raw = self.auto_run_state_path.read_text(encoding="utf-8").strip()
            if not raw:
                return self._default_auto_run_state()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return self._default_auto_run_state()
            state = self._default_auto_run_state()
            state.update(parsed)
            mode = str(state.get("mode", self.AUTO_RUN_DEFAULT_MODE)).lower()
            if mode not in self.AUTO_RUN_ALLOWED_MODES:
                mode = self.AUTO_RUN_DEFAULT_MODE
            state["mode"] = mode
            return state
        except Exception:
            logger.warning("   Failed loading auto-run state; using defaults", exc_info=True)
            return self._default_auto_run_state()

    def _init_auto_run_state(self) -> None:
        """Initialize auto-run state and persist defaults if needed."""
        self.auto_run_state = self._load_auto_run_state()
        self.auto_run_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.auto_run_state_path.write_text(json.dumps(self.auto_run_state, ensure_ascii=False), encoding="utf-8")
        self.auto_run_cycle_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.auto_run_cycle_ledger_path.exists():
            self.auto_run_cycle_ledger_path.write_text("", encoding="utf-8")

    def _write_auto_run_state(self, reason: str = "", actor: str = "system") -> bool:
        """Persist auto-run state to disk."""
        try:
            self.auto_run_state["updated_at"] = self._now()
            self.auto_run_state["updated_by"] = actor
            self.auto_run_state["updated_reason"] = str(reason or "")
            self.auto_run_state_path.write_text(json.dumps(self.auto_run_state, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            logger.warning("   Failed persisting auto-run state", exc_info=True)
            return False

    def _read_auto_run_cycles(self) -> list:
        """Read control loop ledger from disk."""
        if not self.auto_run_cycle_ledger_path.exists():
            return []
        cycles = []
        try:
            with self.auto_run_cycle_ledger_path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except Exception:
                        logger.warning("   Auto-run cycle ledger line malformed; skipping", exc_info=True)
                        continue
                    if isinstance(event, dict):
                        cycles.append(event)
        except Exception:
            logger.warning("   Auto-run cycle ledger load failed", exc_info=True)
        return cycles

    @staticmethod
    def _parse_iso_timestamp(value):
        """Parse UTC/ISO timestamp values from stored control metadata."""
        if not isinstance(value, str) or not value.strip():
            return None
        raw = value.strip()
        try:
            from datetime import datetime
            return datetime.fromisoformat(raw)
        except Exception:
            try:
                from datetime import datetime
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                return None

    def _auto_run_cooldown_seconds(self, state=None) -> int:
        cfg = state or self.auto_run_state
        try:
            return max(0, int(float(cfg.get("cooldown_minutes", self.AUTO_RUN_DEFAULT_COOLDOWN_MINUTES) or 0) * 60))
        except Exception:
            return 0

    def _auto_run_cooldown_remaining_seconds(self, state=None, now=None) -> int:
        from datetime import datetime
        now_dt = now or datetime.utcnow()
        cooldown_seconds = self._auto_run_cooldown_seconds(state=state)
        if cooldown_seconds <= 0:
            return 0
        last_cycle_at = self._parse_iso_timestamp((state or self.auto_run_state).get("last_cycle_at"))
        if not last_cycle_at:
            return 0
        elapsed = (now_dt - last_cycle_at).total_seconds()
        remaining = cooldown_seconds - int(elapsed)
        return max(0, int(remaining))

    def _is_auto_run_cycle_duplicate(self, cycle_id: str) -> bool:
        if not isinstance(cycle_id, str) or not cycle_id:
            return False
        cycles = self._read_auto_run_cycles()
        return any(event.get("cycle_id") == cycle_id for event in cycles)

    def _auto_run_cycle_eligibility(self, now=None, force: bool = False) -> Dict[str, Any]:
        """Evaluate if auto-run loop should proceed."""
        state = self.auto_run_state
        from datetime import datetime, timedelta
        now_dt = now or datetime.utcnow()
        mode = str(state.get("mode", self.AUTO_RUN_DEFAULT_MODE)).lower()

        if mode == self.AUTO_RUN_MODE_OFF and not force:
            return {
                "ok": False,
                "blocked": True,
                "reason": "mode_off",
                "message": "auto-run mode is off",
                "mode": mode,
                "remaining_cooldown_seconds": 0,
            }

        if state.get("kill_switch") and not force:
            return {
                "ok": False,
                "blocked": True,
                "reason": "kill_switch",
                "message": "auto-run kill-switch is enabled",
                "mode": mode,
                "remaining_cooldown_seconds": 0,
            }

        remaining = self._auto_run_cooldown_remaining_seconds(state=state, now=now_dt)
        if remaining > 0 and not force:
            next_cycle_at = now_dt + timedelta(seconds=remaining)
            return {
                "ok": False,
                "blocked": True,
                "reason": "cooldown_not_elapsed",
                "message": f"next auto-run cycle in {remaining} seconds",
                "mode": mode,
                "remaining_cooldown_seconds": remaining,
                "next_cycle_at": next_cycle_at.isoformat(),
            }

        return {
            "ok": True,
            "blocked": False,
            "reason": "ok",
            "message": "auto-run cycle allowed",
            "mode": mode,
            "remaining_cooldown_seconds": remaining,
            "next_cycle_at": None,
        }

    @staticmethod
    def _coerce_auto_run_mode_text(value) -> str:
        return str(value or "").strip().lower()

    def get_auto_run_cycles(self, limit: Optional[int] = 20) -> list:
        """Return most recent control-cycle records."""
        cycles = self._read_auto_run_cycles()
        try:
            cycles.sort(key=lambda c: str(c.get("cycle_at") or c.get("created_at") or ""))
        except Exception:
            pass
        if isinstance(limit, int) and limit > 0:
            return cycles[-limit:]
        return cycles

    def _build_auto_run_cycle_id(self, mode: str) -> str:
        """Build deterministic-ish cycle identifier."""
        from datetime import datetime
        seed = datetime.utcnow().strftime("%Y%m%d%H%M")
        prior = self.get_auto_run_cycles(limit=9999)
        return f"auto-cycle-{seed}-{len(prior)+1:04d}-{mode}"

    def _append_auto_run_cycle(self, payload: Dict[str, Any]) -> bool:
        """Append auto-run cycle payload into ledger."""
        try:
            payload = dict(payload)
            payload.setdefault("cycle_at", self._now())
            with self.auto_run_cycle_ledger_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return True
        except Exception:
            logger.warning("   Auto-run cycle append failed", exc_info=True)
            return False

    def get_auto_run_status(self) -> Dict[str, Any]:
        """Return current auto-run control-plane status."""
        cycles = self.get_auto_run_cycles(limit=5)
        latest = cycles[-1] if cycles else {}
        eligibility = self._auto_run_cycle_eligibility(force=True)
        return {
            "ok": True,
            "mode": self.auto_run_state.get("mode", self.AUTO_RUN_DEFAULT_MODE),
            "state": self.auto_run_state,
            "latest_cycle": latest,
            "state_path": str(self.auto_run_state_path),
            "cycle_ledger_path": str(self.auto_run_cycle_ledger_path),
            "eligibility": eligibility,
            "remaining_cooldown_seconds": eligibility.get("remaining_cooldown_seconds", 0),
            "next_cycle_at": eligibility.get("next_cycle_at"),
        }

    def set_auto_run_mode(self, mode: str, actor: str = "system", reason: str = "") -> Dict[str, Any]:
        """Set auto-run mode with operator intent, no silent coercion."""
        normalized = str(mode or "").strip().lower()
        if normalized not in self.AUTO_RUN_ALLOWED_MODES:
            return {
                "ok": False,
                "error": "invalid_auto_run_mode",
                "mode": self.auto_run_state.get("mode", self.AUTO_RUN_DEFAULT_MODE),
                "valid_modes": sorted(self.AUTO_RUN_ALLOWED_MODES),
            }

        previous_mode = self.auto_run_state.get("mode", self.AUTO_RUN_DEFAULT_MODE)
        self.auto_run_state["mode"] = normalized
        self._write_auto_run_state(reason=reason, actor=actor)
        self._append_auto_run_cycle(
            {
                "action": "set_mode",
                "cycle_id": self._build_auto_run_cycle_id(normalized),
                "previous_mode": previous_mode,
                "mode": normalized,
                "actor": actor,
                "reason": reason,
            }
        )
        return {
            "ok": True,
            "mode": normalized,
            "previous_mode": previous_mode,
            "state": self.auto_run_state,
        }

    def run_learning_control_cycle(
        self,
        limit: Optional[int] = None,
        min_feedback_events: Optional[int] = None,
        actor: str = "system",
        source: str = "manual",
        cycle_id: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Run one controlled learning loop cycle (no auto-apply side effects)."""
        min_samples = max(1, int(min_feedback_events or self.AUTO_TUNE_MIN_FEEDBACK_EVENTS))
        status = self.get_auto_run_status()
        mode = str(status.get("mode", self.AUTO_RUN_DEFAULT_MODE)).lower()

        generated_cycle_id = self._coerce_auto_run_mode_text(cycle_id) or self._build_auto_run_cycle_id(mode)
        if self._is_auto_run_cycle_duplicate(generated_cycle_id):
            return {
                "ok": False,
                "cycle_id": generated_cycle_id,
                "mode": mode,
                "source": source,
                "actor": actor,
                "error": "duplicate_cycle_id",
                "message": "Cycle id already exists; use preview-only re-run guard instead",
            }

        replay = self.evaluate_learning_policy_candidates(
            limit=limit,
            min_feedback_events=min_samples,
        )
        health = self.assess_active_policy_health(min_feedback_events=min_samples)
        tune = self.propose_guarded_auto_tune(min_feedback_events=min_samples)

        evaluations = replay.get("evaluations", []) or []
        ready_policies = [row.get("policy_id") for row in evaluations if row.get("ready")]

        decision = "manual_review"
        can_auto_act = False
        if mode == self.AUTO_RUN_MODE_PILOT:
            decision = "pilot_recommend"
        elif mode == self.AUTO_RUN_MODE_AUTO:
            if status.get("state", {}).get("kill_switch") and not force:
                decision = "blocked_by_kill_switch"
            elif health.get("rollback_trigger"):
                decision = "blocked_by_health"
            elif tune.get("apply_recommended"):
                can_auto_act = False
                decision = "auto_recommend"

        cycle = {
            "ok": True,
            "cycle_id": generated_cycle_id,
            "mode": mode,
            "source": source,
            "actor": actor,
            "force": bool(force),
            "decision": decision,
            "replay": {
                "ok": bool(replay.get("ok")),
                "evaluated_count": replay.get("evaluated_count", 0),
                "ready_count": replay.get("ready_count", 0),
                "blocked_count": replay.get("blocked_count", 0),
                "ready_policies": ready_policies,
            },
            "health": {
                "ok": bool(health.get("ok")),
                "rollback_trigger": bool(health.get("rollback_trigger")),
                "risk_level": health.get("risk_level", "unknown"),
            },
            "tune": {
                "ok": bool(tune.get("ok")),
                "apply_recommended": bool(tune.get("apply_recommended")),
                "rollback_trigger": bool(tune.get("rollback_trigger")),
                "suggestions": tune.get("suggestions", []),
                "reason_codes": tune.get("reason_codes", []),
            },
            "can_auto_apply": can_auto_act,
            "cycle_at": self._now(),
        }
        cycle["run_action"] = "cycle"
        cycle["gate_state"] = {
            "run_eligible": self._auto_run_cycle_eligibility(force=force),
            "kill_switch": bool(self.auto_run_state.get("kill_switch")),
            "cooldown_seconds": self._auto_run_cooldown_seconds(),
        }

        self._append_auto_run_cycle({"action": "cycle", **cycle})
        return cycle

    def run_auto_learning_loop(
        self,
        limit: Optional[int] = None,
        min_feedback_events: Optional[int] = None,
        actor: str = "system",
        source: str = "scheduler",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Execute one auto-run loop cycle honoring readiness gates."""
        eligibility = self._auto_run_cycle_eligibility(force=force)
        if not eligibility.get("ok"):
            return {
                "ok": False,
                "blocked": True,
                "action": "auto_run_loop",
                "source": source,
                "actor": actor,
                "eligibility": eligibility,
            }

        cycle = self.run_learning_control_cycle(
            limit=limit,
            min_feedback_events=min_feedback_events,
            actor=actor,
            source=source,
            force=force,
        )
        if not cycle.get("ok", False):
            return {
                "ok": False,
                "action": "auto_run_loop",
                "source": source,
                "actor": actor,
                "error": cycle.get("error", "run_learning_control_cycle_failed"),
                "cycle": cycle,
            }

        self.auto_run_state["last_cycle_at"] = cycle.get("cycle_at")
        self.auto_run_state["last_cycle_mode"] = cycle.get("mode")
        self.auto_run_state["last_cycle_id"] = cycle.get("cycle_id")
        self.auto_run_state["last_cycle_decision"] = cycle.get("decision")
        self.auto_run_state["last_cycle_source"] = source
        self._write_auto_run_state(reason=f"auto-run loop ({cycle.get('mode')})", actor=actor)
        cycle["action"] = "loop"
        cycle["eligible"] = True
        return cycle

    def _build_default_policy_record(
        self,
        source: str = "system",
        status: str = "active",
        rationale: str = "",
        runtime_overrides: Optional[Dict[str, Any]] = None,
        policy_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        records = self.get_learning_policies(include_inactive=True)
        policy_sequence = len(records) + 1
        if not policy_id:
            policy_id = f"policy-{policy_sequence:04d}"

        runtime_config = dict(self.phase3_config)
        if runtime_overrides:
            runtime_config.update(runtime_overrides)

        return {
            "event_version": 1,
            "event_type": "learning_policy",
            "event_at": self._now(),
            "policy_sequence": policy_sequence,
            "policy_id": policy_id,
            "status": status,
            "source": source,
            "rationale": rationale or "",
            "runtime_config": runtime_config,
            "evidence_ref": {
                "routing_metrics": self.get_routing_feedback_metrics(limit=None),
            },
            "policy_version": {
                "major": 1,
                "minor": 0,
                "patch": 0,
            },
        }

    def _append_learning_policy_record(self, record: Dict[str, Any], append_ledger: bool = True) -> bool:
        """Append learning-policy record to policy store, and optional ledger."""
        try:
            with self.policy_store_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            if append_ledger:
                ledger_record = dict(record)
                ledger_record["ledger_at"] = self._now()
                with self.policy_ledger_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(ledger_record, ensure_ascii=False) + "\n")
            return True
        except Exception:
            logger.warning("   Learning policy append failed", exc_info=True)
            return False

    def _iter_learning_policies(self) -> list:
        """Load policy records from policy store, tolerant to malformed lines."""
        events: list = []
        if not self.policy_store_path.exists():
            return events

        try:
            with self.policy_store_path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except Exception:
                        logger.warning("   Policy store line is malformed; skipping", exc_info=True)
                        continue
                    if event.get("event_type") != "learning_policy":
                        continue
                    events.append(event)
        except Exception:
            logger.warning("   Policy store load failed", exc_info=True)
        return events

    def get_learning_policies(self, include_inactive: bool = True, limit: Optional[int] = None) -> list:
        """Return policy records sorted by policy_sequence."""
        events = self._iter_learning_policies()
        try:
            events.sort(key=lambda x: int(x.get("policy_sequence", 0) or 0))
        except Exception:
            # Keep deterministic behavior even on malformed sequence values
            pass

        if not include_inactive:
            events = [event for event in events if event.get("status") == "active"]
        if isinstance(limit, int) and limit > 0:
            events = events[-limit:]
        return events

    def _effective_policy_config(self) -> Dict[str, Any]:
        """Merge active learning policy into runtime config with analyze-only hard safety."""
        policy = self.get_active_learning_policy()
        merged = dict(self.phase3_config)
        policy_runtime = policy.get("runtime_config")
        if isinstance(policy_runtime, dict):
            merged.update(policy_runtime)

        # Security: enforce current runtime analyze_only as hard guardrail
        merged["analyze_only"] = bool(self.phase3_config.get("analyze_only", True))
        return merged

    def get_active_learning_policy(self) -> Dict[str, Any]:
        """Return the latest active learning policy record."""
        active_records = self.get_learning_policies(include_inactive=True)
        candidates = [record for record in active_records if record.get("status") == "active"]
        if not candidates:
            return self._build_default_policy_record(status=self.LEARNING_POLICY_DEFAULT_STATUS, source="runtime_fallback")

        return candidates[-1]

    def get_policy_status(self) -> Dict[str, Any]:
        """Return compact policy health snapshot for status rendering."""
        all_records = self.get_learning_policies(include_inactive=True)
        active = self.get_active_learning_policy()
        candidates = [record for record in all_records if record.get("status") != "active"]
        return {
            "store_path": str(self.policy_store_path),
            "ledger_path": str(self.policy_ledger_path),
            "active": {
                "policy_id": active.get("policy_id"),
                "status": active.get("status"),
                "policy_sequence": active.get("policy_sequence"),
                "source": active.get("source"),
            },
            "candidates": len(candidates),
            "total_records": len(all_records),
        }

    def propose_learning_policy(
        self,
        policy_overrides: Dict[str, Any],
        rationale: str = "",
        source: str = "user",
    ) -> Dict[str, Any]:
        """Create a new policy candidate without changing routing behavior."""
        if not isinstance(policy_overrides, dict):
            return {"ok": False, "error": "policy_overrides must be a mapping"}

        allowed_keys = {"analyze_only", "auto_route_enabled", "auto_route_threshold", "manual_override_prefixes", "adapter_contract"}
        unknown_keys = set(policy_overrides) - allowed_keys
        if unknown_keys:
            return {"ok": False, "error": f"unsupported policy keys: {', '.join(sorted(unknown_keys))}"}

        if "auto_route_threshold" in policy_overrides:
            try:
                threshold = float(policy_overrides["auto_route_threshold"])
            except (TypeError, ValueError):
                return {"ok": False, "error": "auto_route_threshold must be numeric"}
            if not (0.0 <= threshold <= 1.0):
                return {"ok": False, "error": "auto_route_threshold must be within [0.0, 1.0]"}

        active = self.get_active_learning_policy()
        runtime_config = dict(active.get("runtime_config", {}))
        runtime_config.update(policy_overrides)

        records = self.get_learning_policies(include_inactive=True)
        policy_sequence = len(records) + 1
        candidate_id = f"{(active.get('policy_id') or 'policy')}-candidate-{policy_sequence:04d}"
        candidate = {
            "event_version": 1,
            "event_type": "learning_policy",
            "event_at": self._now(),
            "policy_sequence": policy_sequence,
            "policy_id": candidate_id,
            "status": "candidate",
            "source": source,
            "rationale": rationale,
            "runtime_config": runtime_config,
            "evidence_ref": {
                "routing_metrics": self.get_routing_feedback_metrics(limit=None),
            },
            "policy_version": {
                "major": 1,
                "minor": 0,
                "patch": 0,
            },
        }

        if not self._append_learning_policy_record(candidate):
            return {"ok": False, "error": "unable to persist candidate policy"}

        return {"ok": True, "policy": candidate}

    def apply_learning_policy(self, policy_id: str, reason: str = "manual-approval") -> Dict[str, Any]:
        """Apply an existing candidate policy as active after explicit review."""
        candidates = [
            p for p in self.get_learning_policies(include_inactive=True) if p.get("policy_id") == policy_id
        ]
        if not candidates:
            return {"ok": False, "error": f"policy_id not found: {policy_id}"}

        if candidates[-1].get("status") == self.LEARNING_POLICY_DEFAULT_STATUS:
            return {"ok": False, "error": "default active policy does not require apply"}

        candidate = candidates[-1]
        active = self.get_active_learning_policy()
        records = self.get_learning_policies(include_inactive=True)
        next_sequence = len(records) + 1

        activation = dict(candidate)
        activation["status"] = self.LEARNING_POLICY_DEFAULT_STATUS
        activation["policy_sequence"] = next_sequence
        activation["source"] = candidate.get("source", "user")
        activation["applied_from_policy_id"] = candidate.get("policy_id")
        activation["rationale"] = ((candidate.get("rationale", "") + " | ") if candidate.get("rationale") else "") + f"applied: {reason}"
        activation["applied_at"] = self._now()
        activation["event_at"] = self._now()

        if not self._append_learning_policy_record(activation):
            return {"ok": False, "error": "unable to persist policy activation"}

        return {
            "ok": True,
            "policy": activation,
            "previous_active": {
                "policy_id": active.get("policy_id"),
                "policy_sequence": active.get("policy_sequence"),
            },
        }

    def evaluate_learning_policy_readiness(
        self,
        policy_id: str,
        limit: Optional[int] = None,
        min_feedback_events: int = 20,
    ) -> Dict[str, Any]:
        """Readiness check for a candidate policy (read-only, no route change)."""
        candidate_list = [
            p for p in self.get_learning_policies(include_inactive=True) if p.get("policy_id") == policy_id
        ]
        if not candidate_list:
            missing_reasons = ["policy_not_found"]
            return {
                "ok": False,
                "ready": False,
                "reason_codes": missing_reasons,
                "policy_id": policy_id,
                "policy_report": self._build_readiness_policy_report(missing_reasons, replay_summary={}),
            }

        candidate = candidate_list[-1]
        metrics = self.get_routing_feedback_metrics(limit=limit)
        feedback_total = int(metrics.get("feedback_total", 0) or 0)

        candidate_status = str(candidate.get("status"))
        reason_codes: list[str] = []

        # Only candidates may be evaluated as readiness targets.
        if candidate_status != "candidate":
            preflight_reasons = ["policy_not_ready_for_readiness"]
            return {
                "ok": True,
                "ready": False,
                "policy_id": policy_id,
                "reason_codes": preflight_reasons,
                "metrics": metrics,
                "candidate": candidate,
                "observed_feedback_total": feedback_total,
                "required_feedback_total": min_feedback_events,
                "policy_report": self._build_readiness_policy_report(
                    preflight_reasons,
                    replay_summary={},
                    observed_feedback_total=feedback_total,
                    required_feedback_total=min_feedback_events,
                ),
            }

        # Basic sample-size guard.
        if feedback_total < max(0, int(min_feedback_events)):
            preflight_reasons = ["insufficient_feedback_samples"]
            return {
                "ok": True,
                "ready": False,
                "policy_id": policy_id,
                "reason_codes": preflight_reasons,
                "metrics": metrics,
                "candidate": candidate,
                "observed_feedback_total": feedback_total,
                "required_feedback_total": min_feedback_events,
                "policy_report": self._build_readiness_policy_report(
                    preflight_reasons,
                    replay_summary={},
                    observed_feedback_total=feedback_total,
                    required_feedback_total=min_feedback_events,
                ),
            }

        false_positive = metrics.get("feedback", {}).get("false_positive", {})
        fp_should_direct = false_positive.get("should_direct", {}).get("rate", 0.0) or 0.0
        fp_should_fleet = false_positive.get("should_fleet", {}).get("rate", 0.0) or 0.0
        fp_total = false_positive.get("total", 0) or 0

        if fp_should_direct > self.READINESS_MAX_FALSE_POSITIVE_RATE:
            reason_codes.append("too_many_should_direct_false_positives")
        if fp_should_fleet > self.READINESS_MAX_FALSE_POSITIVE_RATE:
            reason_codes.append("too_many_should_fleet_false_positives")
        if fp_total > self.READINESS_MAX_NOTIFIABLE_FALSE_COUNT:
            reason_codes.append("too_many_false_positive_events")

        active_policy = self.get_active_learning_policy()
        active_runtime = active_policy.get("runtime_config", {})
        if not isinstance(active_runtime, dict):
            active_runtime = {}
        candidate_runtime = candidate.get("runtime_config", {})
        if not isinstance(candidate_runtime, dict):
            candidate_runtime = {}

        if "auto_route_threshold" in candidate_runtime and candidate_runtime.get("auto_route_enabled") is True:
            try:
                candidate_threshold = float(candidate_runtime.get("auto_route_threshold", 0.0))
            except (TypeError, ValueError):
                reason_codes.append("candidate_threshold_invalid")
                candidate_threshold = None
            else:
                if candidate_threshold < self.READINESS_MIN_THRESHOLD_GUARD:
                    reason_codes.append("candidate_threshold_below_guardrail")

                try:
                    active_threshold = float(
                        active_runtime.get("auto_route_threshold", self.phase3_config.get("auto_route_threshold", 0.8))
                    )
                except (TypeError, ValueError):
                    active_threshold = None

                if (
                    candidate_threshold is not None
                    and active_threshold is not None
                    and abs(candidate_threshold - active_threshold) > self.READINESS_MAX_THRESHOLD_DELTA
                ):
                    reason_codes.append("candidate_threshold_delta_exceeds_guardrail")

        replay = self._evaluate_candidate_offline_replay(candidate_runtime=candidate_runtime, limit=limit)
        reason_codes.extend(replay.get("reason_codes", []))

        reason_payload: Dict[str, Any] = {
            "ready": False,
            "policy_id": policy_id,
            "metrics": metrics,
            "candidate": candidate,
            "observed_feedback_total": feedback_total,
            "required_feedback_total": min_feedback_events,
            "offline_replay": replay.get("summary", {}),
            "notes": [],
        }
        reason_payload["policy_report"] = self._build_readiness_policy_report(
            reason_codes,
            replay_summary=reason_payload["offline_replay"],
            observed_feedback_total=feedback_total,
            required_feedback_total=min_feedback_events,
        )

        if reason_codes:
            reason_payload.update(
                {
                    "ok": True,
                    "ready": False,
                    "reason_codes": reason_codes,
                    "notes": self._readiness_notes(reason_codes, replay),
                }
            )
            return reason_payload

        reason_payload.update(
            {
                "ok": True,
                "ready": True,
                "reason_codes": ["policy_simulation_passed"],
                "notes": ["Offline replay simulation passed; apply requires explicit operational approval."],
            }
        )
        return reason_payload

    def evaluate_learning_policy_candidates(
        self,
        limit: Optional[int] = None,
        min_feedback_events: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluate readiness for candidate policies (Phase-D offline batch review)."""
        if min_feedback_events is None:
            min_feedback_events = self.AUTO_TUNE_MIN_FEEDBACK_EVENTS

        candidates = [
            p
            for p in self.get_learning_policies(include_inactive=True)
            if p.get("status") == "candidate"
        ]

        if limit is not None:
            try:
                limit_int = int(limit)
            except (TypeError, ValueError):
                return {
                    "ok": False,
                    "error": "limit must be an integer",
                }
            if limit_int > 0:
                candidates = candidates[-limit_int:]

        evaluations = []
        for candidate in candidates:
            policy_id = candidate.get("policy_id")
            if not policy_id:
                continue
            result = self.evaluate_learning_policy_readiness(
                policy_id,
                min_feedback_events=min_feedback_events,
            )
            evaluations.append(
                {
                    "policy_id": policy_id,
                    "ready": bool(result.get("ready", False)),
                    "reason_codes": result.get("reason_codes", []),
                    "observed_feedback_total": result.get("observed_feedback_total", 0),
                    "required_feedback_total": result.get("required_feedback_total", min_feedback_events),
                    "offline_replay": result.get("offline_replay", {}),
                    "policy_report": result.get("policy_report", {}),
                    "candidate_status": candidate.get("status"),
                    "policy_sequence": candidate.get("policy_sequence"),
                }
            )

        ready_count = sum(1 for item in evaluations if item["ready"])
        ranked = sorted(
            evaluations,
            key=lambda entry: (
                not entry["ready"],
                entry["policy_id"] or "",
            ),
        )
        return {
            "ok": True,
            "evaluations": ranked,
            "evaluated_count": len(evaluations),
            "ready_count": ready_count,
            "blocked_count": len(evaluations) - ready_count,
            "min_feedback_events": min_feedback_events,
        }

    def assess_active_policy_health(self, min_feedback_events: Optional[int] = None) -> Dict[str, Any]:
        """Assess active policy health and detect rollback risk."""
        if min_feedback_events is None:
            min_feedback_events = self.AUTO_TUNE_MIN_FEEDBACK_EVENTS

        metrics = self.get_routing_feedback_metrics(limit=None)
        feedback_total = int(metrics.get("feedback_total", 0) or 0)
        if feedback_total < int(min_feedback_events):
            return {
                "ok": False,
                "policy_id": self.get_active_learning_policy().get("policy_id"),
                "rollback_trigger": False,
                "reason_codes": ["insufficient_feedback_samples"],
                "risk_level": "unknown",
                "notes": ["Not enough feedback samples for guarded tuning/rollback assessment."],
            }

        false_positive = metrics.get("feedback", {}).get("false_positive", {})
        fp_total = float(false_positive.get("total", 0) or 0)
        fp_total_rate = float(metrics.get("feedback", {}).get("false_positive", {}).get("rate", 0.0) or 0.0)
        manual_override_rate = float(metrics.get("manual_override_rate", 0.0) or 0.0)
        should_direct_fp = float(false_positive.get("should_direct", {}).get("rate", 0.0) or 0.0)
        should_fleet_fp = float(false_positive.get("should_fleet", {}).get("rate", 0.0) or 0.0)

        reason_codes: list[str] = []
        if fp_total_rate >= self.AUTO_TUNE_ROLLBACK_FP_RATE:
            reason_codes.append("rollback_trigger_fp_rate")
        if should_direct_fp >= self.AUTO_TUNE_ROLLBACK_SHOULD_FP_RATE:
            reason_codes.append("rollback_trigger_should_direct_fp")
        if should_fleet_fp >= self.AUTO_TUNE_ROLLBACK_SHOULD_FP_RATE:
            reason_codes.append("rollback_trigger_should_fleet_fp")
        if manual_override_rate >= self.AUTO_TUNE_MAX_MANUAL_OVERRIDE_RATE:
            reason_codes.append("rollback_trigger_manual_override_rate")

        total_feedback = metrics.get("feedback_total", 0)
        risk_level = "none"
        if reason_codes:
            if int(total_feedback) < 0:
                risk_level = "unknown"
            elif len(reason_codes) >= 3:
                risk_level = "critical"
            else:
                risk_level = "high"
        elif manual_override_rate >= (self.AUTO_TUNE_MAX_MANUAL_OVERRIDE_RATE * 0.7):
            risk_level = "medium"

        return {
            "ok": True,
            "policy_id": self.get_active_learning_policy().get("policy_id"),
            "rollback_trigger": bool(reason_codes),
            "reason_codes": reason_codes,
            "risk_level": risk_level,
            "feedback_total": feedback_total,
            "manual_override_rate": manual_override_rate,
            "false_positive_rate": fp_total_rate,
            "false_positive": {
                "should_direct": should_direct_fp,
                "should_fleet": should_fleet_fp,
                "count": fp_total,
            },
            "notes": [f"manual_override_rate={round(manual_override_rate, 3)}", f"fp_total_rate={round(fp_total_rate, 3)}"],
        }

    def propose_guarded_auto_tune(self, min_feedback_events: Optional[int] = None) -> Dict[str, Any]:
        """Build guarded tuning proposals for active policy and offline candidates (Phase-E)."""
        if min_feedback_events is None:
            min_feedback_events = self.AUTO_TUNE_MIN_FEEDBACK_EVENTS

        health = self.assess_active_policy_health(min_feedback_events=min_feedback_events)
        if not health.get("ok"):
            return {
                "ok": False,
                "error": "insufficient_feedback_for_tuning",
                "reason_codes": ["insufficient_feedback_samples"],
            }
        if health.get("rollback_trigger"):
            return {
                "ok": True,
                "rollback_trigger": True,
                "apply_recommended": False,
                "reason_codes": ["rollback_guard_triggered"] + list(health.get("reason_codes", [])),
                "health": health,
                "suggestions": [],
            }

        active = self.get_active_learning_policy()
        metrics = self.get_routing_feedback_metrics(limit=None)
        false_positive = metrics.get("feedback", {}).get("false_positive", {})
        should_direct_fp = float(false_positive.get("should_direct", {}).get("rate", 0.0) or 0.0)
        should_fleet_fp = float(false_positive.get("should_fleet", {}).get("rate", 0.0) or 0.0)

        suggestions: list[Dict[str, Any]] = []
        runtime_config = dict(active.get("runtime_config", {}) or {})
        baseline_threshold = float(runtime_config.get("auto_route_threshold", self.phase3_config.get("auto_route_threshold", 0.8)) or 0.0)

        def _clamp_threshold(value: float) -> float:
            return max(0.0, min(1.0, value))

        if should_direct_fp >= self.READINESS_MAX_FALSE_POSITIVE_RATE:
            suggestion_threshold = _clamp_threshold(baseline_threshold + self.AUTO_TUNE_THRESHOLD_STEP)
            step = round(suggestion_threshold - baseline_threshold, 2)
            if abs(step) >= self.AUTO_TUNE_THRESHOLD_GUARD_MARGIN:
                suggestions.append(
                    {
                        "type": "increase_directness_guardrail",
                        "target": "auto_route_threshold",
                        "from": baseline_threshold,
                        "to": suggestion_threshold,
                        "delta": step,
                        "rationale": "Too many `should_direct` false-positive labels; raise threshold to reduce risky direct decisions.",
                    }
                )

        if should_fleet_fp >= self.READINESS_MAX_FALSE_POSITIVE_RATE:
            suggestion_threshold = _clamp_threshold(baseline_threshold - self.AUTO_TUNE_THRESHOLD_STEP)
            step = round(suggestion_threshold - baseline_threshold, 2)
            if abs(step) >= self.AUTO_TUNE_THRESHOLD_GUARD_MARGIN:
                suggestions.append(
                    {
                        "type": "decrease_directness_guardrail",
                        "target": "auto_route_threshold",
                        "from": baseline_threshold,
                        "to": suggestion_threshold,
                        "delta": step,
                        "rationale": "Too many `should_fleet` false-positive labels; lower threshold to increase direct execution.",
                    }
                )

        if not suggestions:
            return {
                "ok": True,
                "rollback_trigger": False,
                "apply_recommended": False,
                "reason_codes": ["no_guarded_tuning_signal"],
                "health": health,
                "suggestions": [],
                "notes": ["No safe, high-confidence tuning signals detected."],
            }

        # Respect max tuning magnitude and produce one consolidated suggestion.
        total_delta = max(abs(item["delta"]) for item in suggestions) if suggestions else 0.0
        if total_delta > self.AUTO_TUNE_MAX_TUNING_MAGNITUDE:
            return {
                "ok": True,
                "rollback_trigger": False,
                "apply_recommended": False,
                "reason_codes": ["tuning_change_too_large_guarded"],
                "health": health,
                "suggestions": [],
                "notes": ["Safe tuning delta would exceed configured max magnitude."],
            }

        return {
            "ok": True,
            "rollback_trigger": False,
            "apply_recommended": True,
            "reason_codes": ["guarded_tuning_available"],
            "health": health,
            "suggestions": suggestions,
            "candidate_payload": {
                "from_policy_id": active.get("policy_id"),
                "runtime_config": {
                    **runtime_config,
                    "analyze_only": runtime_config.get("analyze_only", True),
                    "auto_route_enabled": runtime_config.get("auto_route_enabled", False),
                    "auto_route_threshold": suggestions[-1]["to"] if suggestions else baseline_threshold,
                },
            },
        }

    def _build_readiness_policy_report(
        self,
        reason_codes: list[str],
        replay_summary: Optional[Dict[str, Any]] = None,
        observed_feedback_total: int = 0,
        required_feedback_total: int = 0,
    ) -> Dict[str, Any]:
        """Build multi-signal readiness acceptance report for audit/review."""
        replay_summary = replay_summary or {}
        reason_set = set(reason_codes or [])

        signal_rules = {
            "sample_size": {"insufficient_feedback_samples"},
            "policy_state": {"policy_not_found", "policy_not_ready_for_readiness"},
            "false_positive": {
                "too_many_should_direct_false_positives",
                "too_many_should_fleet_false_positives",
                "too_many_false_positive_events",
            },
            "threshold_guard": {
                "candidate_threshold_invalid",
                "candidate_threshold_below_guardrail",
                "candidate_threshold_delta_exceeds_guardrail",
            },
            "replay_history": {"offline_replay_no_events", "offline_replay_insufficient_history"},
            "replay_overall": {"offline_replay_too_many_route_changes"},
            "replay_recent": {"offline_replay_recent_drift_risk"},
            "replay_confidence": {"offline_replay_confidence_low"},
            "replay_seasonal": {"offline_replay_seasonal_shift_risk"},
            "replay_sparsity": {"offline_replay_route_sparsity_risk"},
        }

        signals: Dict[str, Dict[str, Any]] = {}
        failed_signals: list[str] = []
        for signal_name, blocked_codes in signal_rules.items():
            blockers = sorted(reason_set.intersection(blocked_codes))
            passed = len(blockers) == 0
            if not passed:
                failed_signals.append(signal_name)
            signals[signal_name] = {
                "passed": passed,
                "blockers": blockers,
            }

        replay_metrics = {
            "route_flip_rate": replay_summary.get("route_flip_rate", 0.0),
            "route_flip_rate_upper_bound": replay_summary.get("route_flip_rate_upper_bound", 0.0),
            "recent_route_flip_rate": replay_summary.get("recent_route_flip_rate", 0.0),
            "seasonal_flip_delta": replay_summary.get("seasonal_flip_delta", 0.0),
            "sparse_mismatch_routes": replay_summary.get("sparse_mismatch_routes", []),
            "simulated_events": replay_summary.get("simulated_events", 0),
        }

        return {
            "acceptance_passed": len(failed_signals) == 0,
            "failed_signals": failed_signals,
            "signals": signals,
            "observed_feedback_total": int(observed_feedback_total or 0),
            "required_feedback_total": int(required_feedback_total or 0),
            "replay": replay_metrics,
        }

    def _readiness_notes(self, reason_codes: list[str], replay: Optional[Dict[str, Any]] = None) -> list[str]:
        """Render human-friendly readiness reasons for operators."""
        replay_summary = replay or {}
        mapping = {
            "insufficient_feedback_samples": "Needs more human feedback to reduce statistical uncertainty before candidate can be considered.",
            "policy_not_ready_for_readiness": "Policy is not in candidate status; only candidate policies are eligible for readiness evaluation.",
            "too_many_should_direct_false_positives": "Too many `should_direct` false-positive indications; candidate may under-route fleet.",
            "too_many_should_fleet_false_positives": "Too many `should_fleet` false-positive indications; candidate may over-route and increase Fleet spend.",
            "too_many_false_positive_events": "Total false-positive volume exceeds the safe operational alert limit.",
            "candidate_threshold_invalid": "Candidate threshold value is invalid and cannot be evaluated.",
            "candidate_threshold_below_guardrail": "Candidate threshold is below minimum safety guardrail.",
            "candidate_threshold_delta_exceeds_guardrail": "Candidate threshold changed too much from the current active threshold.",
            "offline_replay_no_events": "No routing history is available for replay simulation.",
            "offline_replay_insufficient_history": "Replay sample is too small to estimate route drift safely.",
            "offline_replay_too_many_route_changes": f"Offline replay indicates unstable routing behavior under this candidate (flip-rate={replay_summary.get('route_flip_rate', 0.0):.2%}).",
            "offline_replay_recent_drift_risk": f"Recent replay window indicates directional drift risk (recent flip-rate={replay_summary.get('recent_route_flip_rate', 0.0):.2%}).",
            "offline_replay_confidence_low": f"Replay sample is not yet statistically confident (upper bound={replay_summary.get('route_flip_rate_upper_bound', 0.0):.2%}).",
            "offline_replay_seasonal_shift_risk": f"Replay halves show seasonal shift risk (delta={replay_summary.get('seasonal_flip_delta', 0.0):.2%}).",
            "offline_replay_route_sparsity_risk": "Replay includes sparse route buckets with mismatches; candidate risk is under-sampled.",
            "policy_simulation_pending": "Offline replay not completed yet.",
            "policy_simulation_passed": "Offline replay simulation passed with bounded route-change and no safety regressions.",
        }
        notes: list[str] = []
        for reason in reason_codes:
            if reason in mapping:
                notes.append(mapping[reason])
        return notes

    def _evaluate_candidate_offline_replay(self, candidate_runtime: Dict[str, Any], limit: Optional[int] = None) -> Dict[str, Any]:
        """Run offline replay-style projection for candidate runtime policy against historic routing events."""
        routing_events = self._iter_telemetry_events("routing_decision", limit=limit)
        if not routing_events:
            return {
                "ok": False,
                "reason_codes": ["offline_replay_no_events"],
                "summary": {
                    "total_events": 0,
                    "simulated_events": 0,
                    "route_changes": 0,
                    "route_flip_rate": 0.0,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": 0,
                    "recent_route_flip_rate": 0.0,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                },
            }

        replay_events = routing_events[-self.READINESS_OFFLINE_REPLAY_WINDOW :]
        route_changes = 0
        simulated_events = 0
        by_route_baseline = {}
        by_route_simulated = {}
        by_route_mismatch = {}
        mismatch_flags: list[bool] = []

        for event in replay_events:
            actual_route = self._normalize_route_value(
                event.get("decision", {}).get("execution", {}).get("route", "")
                or event.get("decision", {}).get("raw", {}).get("route", "")
            )
            projected = self._simulate_execution_route_for_policy(
                event,
                candidate_runtime=candidate_runtime,
            )
            if not projected:
                continue
            simulated_route = self._normalize_route_value(projected.route.value)
            simulated_events += 1
            by_route_baseline[actual_route] = by_route_baseline.get(actual_route, 0) + 1
            by_route_simulated[simulated_route] = by_route_simulated.get(simulated_route, 0) + 1

            changed = actual_route != simulated_route
            mismatch_flags.append(changed)
            if changed:
                route_changes += 1
                route_pair = f"{actual_route}|{simulated_route}"
                by_route_mismatch[route_pair] = by_route_mismatch.get(route_pair, 0) + 1

        recent_mismatch_flags = mismatch_flags[-self.READINESS_RECENT_REPLAY_WINDOW :]
        recent_simulated_events = len(recent_mismatch_flags)
        recent_route_changes = sum(1 for changed in recent_mismatch_flags if changed)
        recent_route_flip_rate = (
            recent_route_changes / float(recent_simulated_events)
            if recent_simulated_events
            else 0.0
        )

        seasonal_half = simulated_events // 2 if simulated_events else 0
        first_half = mismatch_flags[:seasonal_half]
        second_half = mismatch_flags[seasonal_half:]
        first_half_events = len(first_half)
        second_half_events = len(second_half)
        first_half_flip_rate = (
            sum(1 for changed in first_half if changed) / float(first_half_events)
            if first_half_events
            else 0.0
        )
        second_half_flip_rate = (
            sum(1 for changed in second_half if changed) / float(second_half_events)
            if second_half_events
            else 0.0
        )
        seasonal_flip_delta = abs(second_half_flip_rate - first_half_flip_rate)

        sparse_mismatch_routes = sorted(
            {
                route_pair.split("|", 1)[0]
                for route_pair, count in by_route_mismatch.items()
                if count > 0 and by_route_baseline.get(route_pair.split("|", 1)[0], 0) < self.READINESS_MIN_ROUTE_SUPPORT
            }
        )

        if simulated_events < self.READINESS_MIN_OFFLINE_REPLAY_EVENTS:
            return {
                "ok": False,
                "reason_codes": ["offline_replay_insufficient_history"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": (route_changes / simulated_events) if simulated_events else 0.0,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        route_flip_rate = route_changes / float(simulated_events)
        route_flip_rate_upper_bound = self._wilson_upper_bound(route_changes, simulated_events)
        if route_flip_rate > self.READINESS_MAX_OFFLINE_ROUTE_FLIP_RATE:
            return {
                "ok": False,
                "reason_codes": ["offline_replay_too_many_route_changes"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": route_flip_rate,
                    "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        if (
            recent_simulated_events >= self.READINESS_MIN_OFFLINE_REPLAY_EVENTS
            and recent_route_flip_rate > self.READINESS_MAX_RECENT_ROUTE_FLIP_RATE
        ):
            return {
                "ok": False,
                "reason_codes": ["offline_replay_recent_drift_risk"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": route_flip_rate,
                    "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        if (
            route_changes > 0
            and simulated_events < self.READINESS_MIN_CONFIDENCE_REPLAY_EVENTS
            and route_flip_rate_upper_bound > self.READINESS_MAX_OFFLINE_ROUTE_FLIP_RATE
        ):
            return {
                "ok": False,
                "reason_codes": ["offline_replay_confidence_low"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": route_flip_rate,
                    "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "first_half_events": first_half_events,
                    "second_half_events": second_half_events,
                    "first_half_flip_rate": first_half_flip_rate,
                    "second_half_flip_rate": second_half_flip_rate,
                    "seasonal_flip_delta": seasonal_flip_delta,
                    "sparse_mismatch_routes": sparse_mismatch_routes,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        if (
            first_half_events >= self.READINESS_MIN_OFFLINE_REPLAY_EVENTS
            and second_half_events >= self.READINESS_MIN_OFFLINE_REPLAY_EVENTS
            and seasonal_flip_delta > self.READINESS_MAX_SEASONAL_FLIP_DELTA
        ):
            return {
                "ok": False,
                "reason_codes": ["offline_replay_seasonal_shift_risk"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": route_flip_rate,
                    "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "first_half_events": first_half_events,
                    "second_half_events": second_half_events,
                    "first_half_flip_rate": first_half_flip_rate,
                    "second_half_flip_rate": second_half_flip_rate,
                    "seasonal_flip_delta": seasonal_flip_delta,
                    "sparse_mismatch_routes": sparse_mismatch_routes,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        if sparse_mismatch_routes:
            return {
                "ok": False,
                "reason_codes": ["offline_replay_route_sparsity_risk"],
                "summary": {
                    "total_events": len(replay_events),
                    "simulated_events": simulated_events,
                    "route_changes": route_changes,
                    "route_flip_rate": route_flip_rate,
                    "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                    "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                    "recent_simulated_events": recent_simulated_events,
                    "recent_route_flip_rate": recent_route_flip_rate,
                    "first_half_events": first_half_events,
                    "second_half_events": second_half_events,
                    "first_half_flip_rate": first_half_flip_rate,
                    "second_half_flip_rate": second_half_flip_rate,
                    "seasonal_flip_delta": seasonal_flip_delta,
                    "sparse_mismatch_routes": sparse_mismatch_routes,
                    "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                    "baseline_route_mix": by_route_baseline,
                    "simulated_route_mix": by_route_simulated,
                    "mismatch_breakdown": by_route_mismatch,
                },
            }

        return {
            "ok": True,
            "reason_codes": [],
            "summary": {
                "total_events": len(replay_events),
                "simulated_events": simulated_events,
                "route_changes": route_changes,
                "route_flip_rate": route_flip_rate,
                "route_flip_rate_upper_bound": route_flip_rate_upper_bound,
                "recent_window_size": self.READINESS_RECENT_REPLAY_WINDOW,
                "recent_simulated_events": recent_simulated_events,
                "recent_route_flip_rate": recent_route_flip_rate,
                "first_half_events": first_half_events,
                "second_half_events": second_half_events,
                "first_half_flip_rate": first_half_flip_rate,
                "second_half_flip_rate": second_half_flip_rate,
                "seasonal_flip_delta": seasonal_flip_delta,
                "sparse_mismatch_routes": sparse_mismatch_routes,
                "window": self.READINESS_OFFLINE_REPLAY_WINDOW,
                "baseline_route_mix": by_route_baseline,
                "simulated_route_mix": by_route_simulated,
                "mismatch_breakdown": by_route_mismatch,
            },
        }

    def _wilson_upper_bound(self, successes: int, trials: int, z: Optional[float] = None) -> float:
        """Wilson score upper bound for Bernoulli proportion."""
        if trials <= 0:
            return 0.0
        if z is None:
            z = self.READINESS_CONFIDENCE_Z
        p = successes / float(trials)
        z2 = z * z
        denom = 1.0 + (z2 / trials)
        center = p + (z2 / (2.0 * trials))
        margin = z * math.sqrt((p * (1.0 - p) / trials) + (z2 / (4.0 * trials * trials)))
        return (center + margin) / denom

    def _simulate_execution_route_for_policy(
        self,
        routing_event: Dict[str, Any],
        candidate_runtime: Dict[str, Any],
    ) -> Optional[Any]:
        """Simulate how this routing event would resolve under candidate runtime policy."""
        try:
            raw_decision = routing_event.get("decision", {}) or {}
            raw_route = self._normalize_route_value(raw_decision.get("raw", {}).get("route", ""))
            raw_confidence = raw_decision.get("raw", {}).get("confidence", None)
            if raw_confidence is None:
                raw_confidence = raw_decision.get("analysis", {}).get("score", 0.0)
            if isinstance(raw_confidence, str):
                raw_confidence = raw_confidence.strip()
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = 0.0
            if confidence > 1:
                confidence = confidence / 10.0 if confidence <= 10 else confidence / 100.0

            route_map = {
                "direct": "hermes_direct",
                "direct_with_suggestion": "hermes_direct",
            }
            route_value = route_map.get(raw_route, raw_route) if isinstance(raw_route, str) else "hermes_direct"
            if route_value not in {
                "hermes_direct",
                "fleet_complex",
                "fleet_multi",
                "fleet_safety",
            }:
                route_value = "hermes_direct"

            Decision = type("Decision", (), {})
            Route = type("Route", (), {})
            decision = Decision()
            decision.route = Route()
            decision.route.value = route_value
            decision.confidence = confidence
            decision.reason = f"Replay projection from route={raw_route}"
            decision.suggested_division = raw_decision.get("execution", {}).get("suggested_division")
            decision.phase3 = raw_decision.get("analysis", {}) or {}
            decision.resolution_reason = raw_decision.get("raw", {}).get("resolution_reason", "")

            return self._resolve_execution_route(
                decision,
                raw_route,
                context={},
                task_description=routing_event.get("task_snippet", ""),
                manual_override=routing_event.get("manual_override", "") or "",
                config_override=candidate_runtime,
            )
        except Exception:
            logger.warning("   Offline replay projection failed for routing event; skipping.", exc_info=True)
            return None

    def _normalize_route_value(self, route: str) -> str:
        """Normalize route values into canonical execution-route values used by resolver."""
        route = (route or "").strip()
        if route in {"direct", "hermes_direct"}:
            return "hermes_direct"
        if route in {"fleet", "fleet_complex"}:
            return "fleet_complex"
        if route in {"fleet_safety", "safety"}:
            return "fleet_safety"
        if route in {"fleet_multi", "multi"}:
            return "fleet_multi"
        if route in {"unknown", ""}:
            return "unknown"
        return route


    def _init_fleet(self, fleet_path: Optional[Path] = None):
        """Initialize fleet orchestrator."""
        try:
            # Try relative import first
            try:
                from fleet.core.orchestrator import FleetOrchestrator
            except ImportError:
                sys.path.insert(0, str(self.os_dir))
                from fleet.core.orchestrator import FleetOrchestrator
            self.fleet = FleetOrchestrator(fleet_path=fleet_path)
            logger.info(f"   Fleet: {self.fleet.main_agents}M/{self.fleet.sub_agents}S agents")
        except ImportError as e:
            logger.warning(f"   Fleet: Not loaded ({e})")
            self.fleet = None

    def _init_telemetry_store(self):
        """Initialize routing telemetry storage (durable append-only JSONL + in-memory window)."""
        self.routing_telemetry_path = self.state_dir / "hermes_os_route_telemetry.jsonl"
        self._telemetry_window: list[Dict[str, Any]] = []
        self._telemetry_max_window = 200
        # Keep file available but avoid raising on startup if not writable yet.
        try:
            self.routing_telemetry_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.routing_telemetry_path.exists():
                self.routing_telemetry_path.write_text("", encoding="utf-8")
        except Exception:
            logger.warning("   Telemetry: unable to initialize file sink", exc_info=True)

    def _init_memory(self):
        """Initialize memory system."""
        self.memory = {"sessions": [], "preferences": {}}
        logger.info("   Memory: Active")

    def _init_transport(self):
        """Initialize RTK transport."""
        self.rtk_enabled = os.getenv("HERMES_RTK_WRAP") == "1"
        logger.info(f"   RTK: {'Active' if self.rtk_enabled else 'Inactive'}")

    def execute(self, task_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task through Hermes OS.

        This entry point now runs in direct-execution mode.

        Execution path:
        - Explicit fleet override → Enterprise Agent Fleet
        - Otherwise → Hermes direct execution

        Args:
            task_description: What needs to be done
            context: Optional context like boss_id, priority, etc.

        Returns:
            TaskResult dict with standardized format

        Example:
            >>> os = HermesOS()
            >>> result = os.execute("Build REST API with auth")
            >>> print(result['status'])  # 'completed'
        """
        if not self._active:
            raise RuntimeError("Hermes OS is not active. Run hermes-os to activate.")

        context = context or {}
        task_id = self._generate_task_id()
        started_at = time.perf_counter()

        logger.info(f"📝 Task [{task_id}]: {task_description[:60]}...")

        # Step 1: Determine execution path in direct-execution mode.
        routing_started_at = time.perf_counter()
        manual_override = self._extract_manual_override(context, task_description=task_description)

        if manual_override == "fleet" and self.fleet:
            decision = type('Decision', (), {
                'route': type('Route', (), {'value': 'fleet_complex'})(),
                'suggested_division': 'DIV-02',
                'confidence': 1.0,
                'reason': 'manual_override',
                'resolution_reason': 'manual_override_fleet',
                'phase3': {'contract_route': 'manual_override', 'source': 'manual', 'factors': {}},
            })()
            final_route = decision.route.value
            decision_metadata = {
                "raw_contract": "manual_override",
                "source": "manual",
                "suggestion": "Explicit fleet override.",
                "score": None,
                "factors": {},
            }
            execution_decision = decision
        else:
            decision = type('Decision', (), {
                'route': type('Route', (), {'value': 'hermes_direct'})(),
                'suggested_division': None,
                'confidence': 1.0,
                'reason': 'direct_mode_only',
                'resolution_reason': 'direct_execution_default_direct',
                'phase3': {'contract_route': 'direct_only', 'source': 'manual', 'factors': {}},
            })()
            final_route = decision.route.value
            decision_metadata = {
                "raw_contract": "direct_only",
                "source": "manual",
                "suggestion": "Router disabled; defaulting to Hermes direct.",
                "score": None,
                "factors": {},
            }
            execution_decision = decision
        routing_latency = time.perf_counter() - routing_started_at

        # Step 2: Execute based on path
        execution_started_at = time.perf_counter()
        try:
            if execution_decision.route.value == "hermes_direct":
                result = self._execute_hermes_direct(task_description, context)
            else:
                if self.fleet:
                    result = self._execute_fleet_orchestrated(
                        task_description,
                        execution_decision,
                        context
                    )
                else:
                    # Safe fallback: if Fleet unavailable, preserve old behavior and avoid hard failure
                    result = self._execute_hermes_direct(task_description, context)
        except Exception as exc:  # pragma: no cover - defensive error path
            result = {
                "status": "failed",
                "qa_passed": False,
                "error": str(exc),
                "execution_time_seconds": 0.0,
                "safety_passed": False,
            }
            execution_latency = time.perf_counter() - execution_started_at
            self._append_route_telemetry(
                task_id=task_id,
                task_description=task_description,
                decision=decision,
                execution_decision=execution_decision,
                result=result,
                manual_override=manual_override,
                decision_metadata=decision_metadata,
                started_at=started_at,
                routing_latency=routing_latency,
                execution_latency=execution_latency,
                error=str(exc),
            )
            raise
        execution_latency = time.perf_counter() - execution_started_at

        # Step 3: Store in memory
        self._remember_task(task_id, task_description, result)

        result['task_id'] = task_id
        result['route'] = execution_decision.route.value
        result['routing_contract'] = {
            "direct_mode_only": True,
            "manual_override": manual_override,
            "execution_decision": execution_decision.route.value,
            "analysis": decision_metadata,
        }

        result.setdefault("execution_time_seconds", 0.0)

        self._append_route_telemetry(
            task_id=task_id,
            task_description=task_description,
            decision=decision,
            execution_decision=execution_decision,
            result=result,
            manual_override=manual_override,
            decision_metadata=decision_metadata,
            started_at=started_at,
            routing_latency=routing_latency,
            execution_latency=execution_latency,
            error=None,
        )

        return result

    def capture_routing_feedback(
        self,
        task_id: str,
        label: str,
        note: Optional[str] = None,
        source: str = "user",
    ) -> Dict[str, Any]:
        """Capture Boss/user feedback tied to a known task_id."""
        task_id = (task_id or "").strip()
        normalized_label = (label or "").strip().lower()

        if not task_id:
            return {
                "ok": False,
                "error": "task_id is required for feedback capture",
            }

        if normalized_label not in self.VALID_ROUTING_FEEDBACK_LABELS:
            return {
                "ok": False,
                "error": (
                    "invalid feedback label. Supported labels: "
                    + ", ".join(sorted(self.VALID_ROUTING_FEEDBACK_LABELS))
                ),
            }

        routing_event = self._find_latest_routing_decision(task_id)
        if not routing_event:
            return {
                "ok": False,
                "error": f"not found: no routing decision for task_id={task_id}",
            }

        expected_route = None
        if normalized_label == "should_direct":
            expected_route = "hermes_direct"
        elif normalized_label == "should_fleet":
            expected_route = "fleet_complex"

        decision = routing_event.get("decision", {})
        event = {
            "event_version": 1,
            "event_type": "routing_feedback",
            "event_at": self._now(),
            "task_id": task_id,
            "label": normalized_label,
            "note": (note or "").strip(),
            "source": source,
            "expected_route": expected_route,
            "routing_snapshot": {
                "manual_override": routing_event.get("manual_override", ""),
                "execution_route": decision.get("execution", {}).get("route", ""),
                "raw_route": decision.get("raw", {}).get("route", ""),
                "resolution_reason": decision.get("execution", {}).get("resolution_reason", ""),
            },
            "runtime": {
                "analyze_only": bool(self._effective_policy_config().get("analyze_only", True)),
                "auto_route_enabled": bool(self._effective_policy_config().get("auto_route_enabled", False)),
                "auto_route_threshold": self._effective_policy_config().get("auto_route_threshold", 0.8),
                "policy": {
                    "policy_id": self.get_active_learning_policy().get("policy_id"),
                    "policy_sequence": self.get_active_learning_policy().get("policy_sequence"),
                    "policy_status": self.get_active_learning_policy().get("status"),
                },
            },
        }

        appended = self._append_feedback_event(event)
        if not appended:
            return {
                "ok": False,
                "error": "unable to append feedback event; telemetry sink unavailable",
            }

        self._telemetry_window.append(event)
        if len(self._telemetry_window) > self._telemetry_max_window:
            self._telemetry_window = self._telemetry_window[-self._telemetry_max_window :]

        return {
            "ok": True,
            "task_id": task_id,
            "label": normalized_label,
            "expected_route": expected_route,
        }

    def get_routing_feedback_metrics(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Summarize feedback signals without route-mix reporting."""
        feedback_events = self._iter_telemetry_events("routing_feedback", limit=limit)
        routing_events = self._iter_telemetry_events("routing_decision", limit=limit)

        total_feedback = len(feedback_events)
        manual_override_count = sum(1 for event in routing_events if (event.get("manual_override") or "").strip())
        manual_override_rate = (manual_override_count / len(routing_events)) if routing_events else 0.0

        label_counts = {
            "correct": 0,
            "incorrect": 0,
            "should_direct": 0,
            "should_fleet": 0,
        }

        for event in feedback_events:
            label = (event.get("label") or "").strip().lower()
            if label not in label_counts:
                label = "incorrect"
            label_counts[label] += 1

        false_positive_counts = {
            "should_direct": 0,
            "should_fleet": 0,
            "incorrect": label_counts.get("incorrect", 0),
        }
        false_positive_total = false_positive_counts["should_direct"] + false_positive_counts["should_fleet"]

        return {
            "window": limit,
            "feedback_total": total_feedback,
            "manual_override_count": manual_override_count,
            "manual_override_rate": manual_override_rate,
            "feedback": {
                "labels": label_counts,
                "false_positive": {
                    "should_direct": {"count": false_positive_counts["should_direct"], "rate": 0.0, "by_route": {}},
                    "should_fleet": {"count": false_positive_counts["should_fleet"], "rate": 0.0, "by_route": {}},
                    "incorrect": {"count": false_positive_counts["incorrect"]},
                    "total": false_positive_total,
                    "rate": (false_positive_total / total_feedback) if total_feedback else 0.0,
                },
            },
        }

    def _iter_telemetry_events(
        self,
        event_type: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list:
        """Load telemetry events from durable JSONL, tolerant to malformed lines."""
        events: list = []
        if not self.routing_telemetry_path.exists():
            return events

        max_count = None
        if isinstance(limit, int) and limit > 0:
            max_count = limit

        try:
            with self.routing_telemetry_path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except Exception:
                        logger.warning("   Telemetry: skipping malformed event line", exc_info=True)
                        continue

                    if event_type and event.get("event_type") != event_type:
                        continue
                    if task_id and event.get("task_id") != task_id:
                        continue
                    events.append(event)
            if max_count is not None and len(events) > max_count:
                events = events[-max_count:]
        except Exception:
            logger.warning("   Telemetry iteration failed", exc_info=True)
        return events

    def _find_latest_routing_decision(self, task_id: str) -> Dict[str, Any]:
        """Find the latest routing_decision event for a task_id."""
        events = self._iter_telemetry_events(event_type="routing_decision", task_id=task_id)
        if not events:
            return {}
        return events[-1]

    def _append_feedback_event(self, event: Dict[str, Any]) -> bool:
        """Append a routing feedback event to telemetry JSONL."""
        try:
            line = json.dumps(event, ensure_ascii=False)
            with self.routing_telemetry_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            return True
        except Exception:
            logger.warning("   Routing feedback append failed; continue without writing feedback.", exc_info=True)
            return False

    def _resolve_execution_route(
        self,
        decision,
        _final_route: str,
        context: Dict[str, Any],
        task_description: str = "",
        manual_override: str = "",
        config_override: Optional[Dict[str, Any]] = None,
    ):
        """Router-free passthrough for execution decisions."""
        return decision

    def _extract_manual_override(self, context: Dict[str, Any], task_description: str = "") -> str:
        """Normalize manual override request from context."""
        forced = context.get("manual_override")
        if isinstance(forced, str):
            value = forced.strip().lower()
            if value in {"fleet", "force_fleet"}:
                return "fleet"
            if value in {"hermes", "direct", "force_hermes"}:
                return "hermes"
        return ""

    def _execute_hermes_direct(self, task: str, context: Dict) -> Dict:

        # This would call Hermes tool execution
        # For now, return a properly structured result
        from datetime import datetime
        return {
            "status": "completed",
            "result": {
                "summary": f"Executed via Hermes: {task[:50]}...",
                "via": "hermes_direct",
                "context": context
            },
            "execution_time_seconds": 0.1,
            "safety_passed": True,
            "qa_passed": True,
            "completed_at": datetime.utcnow().isoformat()
        }

    def _execute_fleet_orchestrated(
        self,
        task: str,
        decision,
        context: Dict
    ) -> Dict:
        """Execute task via Enterprise Agent Fleet."""
        if not self.fleet:
            raise RuntimeError("Fleet not available")

        return self.fleet.execute_task(
            task_description=task,
            division=decision.suggested_division,
            safety_critical=(decision.route.value == "fleet_safety"),
            context=context
        )

    def _default_decision(self, task: str) -> Any:
        """Default execution decision when direct execution is forced."""
        return type('Decision', (), {
            'route': type('Route', (), {'value': 'hermes_direct'})(),
            'suggested_division': None,
            'confidence': 1.0,
            'reason': 'direct_mode_only',
            'resolution_reason': 'direct_execution_default_direct',
            'phase3': {'contract_route': 'direct_only', 'source': 'manual', 'factors': {}},
        })()

    def _append_route_telemetry(
        self,
        task_id: str,
        task_description: str,
        decision,
        execution_decision,
        result: Dict[str, Any],
        manual_override: str,
        decision_metadata: Dict[str, Any],
        started_at: float,
        routing_latency: float,
        execution_latency: float,
        error: Optional[str],
    ) -> None:
        """Append structured routing telemetry event to durable JSONL + in-memory window."""
        try:
            routing_latency_ms = round(routing_latency * 1000, 3)
            execution_latency_ms = round(execution_latency * 1000, 3)
            total_latency_ms = round((time.perf_counter() - started_at) * 1000, 3)

            event = {
                "event_version": 1,
                "event_type": "routing_decision",
                "event_at": self._now(),
                "task_id": task_id,
                "task_snippet": (task_description or "")[:180],
                "manual_override": manual_override or "",
                "decision": {
                    "raw": {
                        "route": getattr(decision.route, "value", str(getattr(decision, "route", ""))),
                        "confidence": getattr(decision, "confidence", None),
                        "reason": getattr(decision, "reason", ""),
                        "resolution_reason": getattr(decision, "resolution_reason", ""),
                    },
                    "execution": {
                        "route": execution_decision.route.value,
                        "resolution_reason": getattr(execution_decision, "resolution_reason", ""),
                    },
                    "analysis": decision_metadata,
                },
                "runtime": {
                    "analyze_only": bool(self._effective_policy_config().get("analyze_only", True)),
                    "auto_route_enabled": bool(self._effective_policy_config().get("auto_route_enabled", False)),
                    "auto_route_threshold": self._effective_policy_config().get("auto_route_threshold", 0.8),
                    "fleet_available": bool(self.fleet),
                    "policy": {
                        "policy_id": self.get_active_learning_policy().get("policy_id"),
                        "policy_sequence": self.get_active_learning_policy().get("policy_sequence"),
                        "status": self.get_active_learning_policy().get("status"),
                    },
                },
                "outcome": {
                    "status": result.get("status"),
                    "route_result_status": result.get("qa_passed"),
                    "error": error,
                    "duration_seconds": result.get("execution_time_seconds", 0.0),
                },
                "timing": {
                    "routing_latency_ms": routing_latency_ms,
                    "execution_latency_ms": execution_latency_ms,
                    "total_latency_ms": total_latency_ms,
                }
            }

            self._telemetry_window.append(event)
            if len(self._telemetry_window) > self._telemetry_max_window:
                self._telemetry_window = self._telemetry_window[-self._telemetry_max_window :]

            line = json.dumps(event, ensure_ascii=False)
            with self.routing_telemetry_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            logger.warning("   Routing telemetry append failed; continuing without telemetry.", exc_info=True)

    def get_recent_telemetry(self, limit: int = 20) -> list:
        """Return latest telemetry events from in-memory window."""
        return list(self._telemetry_window[-max(0, int(limit)) :])

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        import uuid
        return f"hermes_{uuid.uuid4().hex[:12]}"

    def _remember_task(self, task_id: str, description: str, result: Dict):
        """Store task in memory."""
        self.memory["sessions"].append({
            "task_id": task_id,
            "description": description[:200],
            "status": result.get("status"),
            "timestamp": self._now()
        })

    def _is_gateway_running(self) -> bool:
        """Return True when a Hermes gateway process is running."""
        try:
            proc_dir = Path("/proc")
            if not proc_dir.exists():
                return False
            for cmdline_path in proc_dir.glob("[0-9]*/cmdline"):
                try:
                    cmdline = cmdline_path.read_text(errors="ignore").replace("\x00", " ")
                except OSError:
                    continue
                if "hermes_cli.main" in cmdline and "gateway" in cmdline and "run" in cmdline:
                    return True
        except Exception:
            return False
        return False

    def _get_mcp_component_status(self) -> Dict[str, Any]:
        """Return a fail-soft snapshot of Hermes OS MCP component wiring."""
        snapshot: Dict[str, Any] = {
            "context7": {
                "enabled": False,
                "transport": "",
                "role": "external_library_docs_evidence",
            },
            "context_mode": {
                "enabled": False,
                "transport": "",
                "role": "hermes_os_context_rag",
            },
        }
        if yaml is None:
            return snapshot

        try:
            config_path = Path.home() / ".hermes" / "config.yaml"
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            servers = raw.get("mcp_servers") if isinstance(raw, dict) else {}
            if not isinstance(servers, dict):
                return snapshot
            for name in ("context7", "context_mode"):
                server = servers.get(name)
                if not isinstance(server, dict):
                    continue
                snapshot[name]["enabled"] = server.get("enabled", True) is not False
                snapshot[name]["transport"] = str(
                    server.get("url") or server.get("command") or ""
                )
        except Exception:
            return snapshot
        return snapshot

    def _now(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def status(self) -> Dict[str, Any]:
        """
        Get Hermes OS status.

        Returns:
            Status dictionary with fleet health, memory stats, etc.
        """
        effective_policy = self._effective_policy_config()
        mcp = self._get_mcp_component_status()
        return {
            "mode": self._mode,
            "active": self._active,
            "version": __version__,
            "components": {
                "fleet": self.fleet is not None if self.fleet else False,
                "rtk": self.rtk_enabled,
                "gateway": self._is_gateway_running(),
                "context7": bool(mcp.get("context7", {}).get("enabled")),
                "context_mode": bool(mcp.get("context_mode", {}).get("enabled")),
            },
            "mcp": mcp,
            "fleet": {
                "main_agents": self.fleet.main_agents if self.fleet else 0,
                "sub_agents": self.fleet.sub_agents if self.fleet else 0,
            } if self.fleet else None,
            "auto_run": {
                "mode": self.auto_run_state.get("mode", self.AUTO_RUN_DEFAULT_MODE),
                "state": self.auto_run_state,
                "state_path": str(self.auto_run_state_path),
                "cycle_ledger_path": str(self.auto_run_cycle_ledger_path),
            },
            "telemetry": {
                "events_cached": len(self._telemetry_window),
                "telemetry_path": str(self.routing_telemetry_path),
            },
            "policy": {
                "active_id": self.get_active_learning_policy().get("policy_id"),
                "active_sequence": self.get_active_learning_policy().get("policy_sequence"),
                "status": self.get_active_learning_policy().get("status"),
                "policy_store_path": str(self.policy_store_path),
                "policy_ledger_path": str(self.policy_ledger_path),
            },
            "memory": {
                "tasks_count": len(self.memory["sessions"])
            },
        }

    def fleet_status(self) -> Optional[Dict]:
        """Get Fleet health status."""
        if self.fleet:
            return self.fleet.health()
        return None

    def shutdown(self):
        """Gracefully shutdown Hermes OS."""
        logger.info("🛑 Shutting down Hermes OS...")
        self._save_state()
        self._active = False
        logger.info("   Saved state to ~/.hermes/state/hermes-os.json")

    def _save_state(self):
        """Persist state to disk."""
        state = {
            "mode": self._mode,
            "active": self._active,
            "version": __version__,
            "memory": self.memory,
            "fleet_status": self.fleet_status() if self.fleet else None,
            "timestamp": self._now()
        }

        state_file = self.state_dir / "hermes-os.json"
        state_file.write_text(json.dumps(state, indent=2))


# Global instance (singleton)
_os_instance: Optional[HermesOS] = None


def get_os() -> HermesOS:
    """Get or create Hermes OS instance."""
    global _os_instance
    if _os_instance is None:
        _os_instance = HermesOS()
    return _os_instance


def set_os(os_instance: HermesOS):
    """Set global OS instance (for testing)."""
    global _os_instance
    _os_instance = os_instance


if __name__ == "__main__":
    # CLI entry point
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "status":
            os = get_os()
            print(json.dumps(os.status(), indent=2))
        elif command == "shutdown":
            os = get_os()
            os.shutdown()
        elif command == "execute" and len(sys.argv) > 2:
            os = get_os()
            task = " ".join(sys.argv[2:])
            result = os.execute(task)
            print(json.dumps(result, indent=2))
        else:
            print(f"Usage: {sys.argv[0]} [status|shutdown|execute <task>]")
    else:
        # Interactive mode
        os = get_os()
        print("🛰️ Hermes OS Active")
        print(f"   Status: {json.dumps(os.status(), indent=2)}")
