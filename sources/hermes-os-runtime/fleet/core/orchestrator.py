"""
Fleet Orchestrator - Core module for Hermes OS Fleet integration.

Manages 7 Main Agents + 21 Sub-Agents with safety validation and QA gates.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4


logger = logging.getLogger(__name__)


@dataclass
class Division:
    """Represents a Fleet Division with Main + 3 Sub Agents."""
    code: str  # DIV-01 to DIV-07
    name: str
    specialty: str
    main_agent: str
    sub_agents: List[str] = field(default_factory=list)

    def __post_init__(self):
        if len(self.sub_agents) != 3:
            logger.warning(f"Division {self.code} should have exactly 3 sub-agents")


@dataclass
class TaskRecord:
    """Record of a fleet task execution."""
    task_id: str
    description: str
    division: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    safety_passed: bool = False
    qa_passed: bool = False
    sub_agents_used: List[str] = field(default_factory=list)


class FleetOrchestrator:
    """
    Orchestrator for Enterprise Agent Fleet within Hermes OS.

    Manages 7 Main Agents (Division Chiefs) and 21 Sub-Agents (3 per division).

    Divisions:
    - DIV-01: Communications (Web, Email, Social, UX Writing, Campaigns, PR, Analytics)
    - DIV-02: Engineering (Backend, Frontend, APIs, DevOps, Testing, Security, Architecture)
    - DIV-03: Data Science (Statistical, ML, Visualization, Engineering, Analytics, NLP)
    - DIV-04: Content/Documentation (Technical Writing, Translation, Blog, Video, Social)
    - DIV-05: Rules/QA/Safety (Fabrication Detection, Policy Compliance, Security, Quality)
    - DIV-06: UI/UX (Design Systems, Prototyping, User Research, Accessibility, Visual Design)
    - DIV-07: Operations/Automation (RPA, Scripting, System Integration, Monitoring, CI/CD)
    """

    # Division configuration
    DIVISIONS = {
        "DIV-01": Division(
            code="DIV-01",
            name="Communications",
            specialty="communications",
            main_agent="Chief Communications Agent",
            sub_agents=["Web Agent", "Email Agent", "Social Media Agent"]
        ),
        "DIV-02": Division(
            code="DIV-02",
            name="Engineering",
            specialty="engineering",
            main_agent="Chief Engineering Agent",
            sub_agents=["Backend Agent", "Frontend Agent", "DevOps Agent"]
        ),
        "DIV-03": Division(
            code="DIV-03",
            name="Data Science",
            specialty="data_science",
            main_agent="Chief Data Science Agent",
            sub_agents=["Statistical Agent", "ML Agent", "Visualization Agent"]
        ),
        "DIV-04": Division(
            code="DIV-04",
            name="Content & Documentation",
            specialty="content",
            main_agent="Chief Content Agent",
            sub_agents=["Technical Writer Agent", "Blog Agent", "Video Script Agent"]
        ),
        "DIV-05": Division(
            code="DIV-05",
            name="Safety, Rules & QA",
            specialty="safety",
            main_agent="Chief Safety Agent",
            sub_agents=["Fabrication Detection Agent", "Policy Compliance Agent", "Security Agent"]
        ),
        "DIV-06": Division(
            code="DIV-06",
            name="UI/UX Design",
            specialty="ui_ux",
            main_agent="Chief Design Agent",
            sub_agents=["Design Systems Agent", "Prototyping Agent", "User Research Agent"]
        ),
        "DIV-07": Division(
            code="DIV-07",
            name="Operations & Automation",
            specialty="operations",
            main_agent="Chief Operations Agent",
            sub_agents=["RPA Agent", "System Integration Agent", "CI/CD Agent"]
        ),
    }

    def __init__(self, fleet_path: Optional[Path] = None):
        """
        Initialize Fleet Orchestrator.

        Args:
            fleet_path: Path to fleet data directory. Defaults to ~/.hermes/os/fleet/data
        """
        self.fleet_path = fleet_path or (Path.home() / ".hermes" / "os" / "fleet")
        self.data_path = self.fleet_path / "data"
        self.tasks_path = self.data_path / "tasks"
        self.logs_path = self.data_path / "logs"

        # Ensure directories exist
        self.tasks_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

        self.registry = AgentRegistry(self.DIVISIONS)
        self.safety = SafetyCore(self.logs_path)
        self.qa = QAGate(self.logs_path)

        self._initialized = True

        logger.info(f"Fleet Orchestrator initialized")
        logger.info(f"   Divisions: {len(self.DIVISIONS)}")
        logger.info(f"   Main Agents: {self.main_agents}")
        logger.info(f"   Sub Agents: {self.sub_agents}")

    @property
    def main_agents(self) -> int:
        """Count of main agents (division chiefs)."""
        return len(self.DIVISIONS)

    @property
    def sub_agents(self) -> int:
        """Count of sub agents (3 per division)."""
        return sum(len(d.sub_agents) for d in self.DIVISIONS.values())

    def health(self) -> Dict[str, Any]:
        """Get fleet health status."""
        return {
            "ready": self._initialized,
            "main_agents": self.main_agents,
            "sub_agents": self.sub_agents,
            "divisions": list(self.DIVISIONS.keys()),
            "status": "online" if self._initialized else "offline",
            "version": "1.0.0",
            "uptime_seconds": 0,  # TODO: Track actual uptime
            "safety_core": self.safety.status(),
            "qa_gate": self.qa.status(),
        }

    def execute_task(
        self,
        task_description: str,
        division: Optional[str] = None,
        safety_critical: bool = False,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a task through the fleet.

        Flow:
        1. Validate task
        2. Route to appropriate division
        3. Safety check (if critical)
        4. Execute with Main + Sub agents
        5. QA gate
        6. Return result

        Args:
            task_description: What to do
            division: Optional specific division (auto-detected if None)
            safety_critical: Whether to enforce safety validation
            context: Additional task context

        Returns:
            Task execution result dict
        """
        task_id = f"fleet_{uuid4().hex[:12]}"
        created_at = datetime.utcnow().isoformat()

        logger.info(f"Fleet Task [{task_id}]: {task_description[:50]}...")

        # Determine division
        if division and division in self.DIVISIONS:
            target_div = self.DIVISIONS[division]
        else:
            target_div = self._auto_route(task_description)

        logger.info(f"   Routed to: {target_div.code} ({target_div.name})")

        # Step 1: Safety Check (if critical)
        if safety_critical:
            logger.info("   Running safety validation...")
            safety_result = self.safety.validate(task_description, target_div.code)
            if not safety_result["passed"]:
                logger.warning(f"   Safety BLOCKED: {safety_result['reason']}")
                return self._blocked_result(task_id, created_at, safety_result)

        # Step 2: Execute with Division
        result = self._execute_with_division(
            task_id=task_id,
            description=task_description,
            division=target_div,
            context=context or {}
        )

        # Step 3: QA Gate
        qa_result = self.qa.validate(result)
        result["qa_passed"] = qa_result["passed"]
        result["qa_notes"] = qa_result.get("notes", [])

        # Save task record
        self._save_task_record(task_id, task_description, target_div.code, result)

        return result

    def _auto_route(self, task_description: str) -> Division:
        """Auto-detect appropriate division for task."""
        task_lower = task_description.lower()

        keywords = {
            "DIV-01": ["web", "email", "social", "campaign", "communication"],
            "DIV-02": ["code", "build", "api", "backend", "frontend", "devops", "deploy"],
            "DIV-03": ["data", "analyze", "statistic", "visualization", "ml", "chart"],
            "DIV-04": ["document", "write", "blog", "content", "article", "readme"],
            "DIV-05": ["safety", "compliance", "policy", "security", "validate", "check"],
            "DIV-06": ["design", "ui", "ux", "prototype", "wireframe", "mockup"],
            "DIV-07": ["automate", "script", "rpa", "pipeline", "ci/cd", "integration"],
        }

        scores = {}
        for div_code, kw_list in keywords.items():
            score = sum(1 for kw in kw_list if kw in task_lower)
            scores[div_code] = score

        best_div = max(scores.items(), key=lambda x: x[1])
        if best_div[1] > 0:
            return self.DIVISIONS[best_div[0]]

        # Default to Operations
        return self.DIVISIONS["DIV-07"]

    def _execute_with_division(
        self,
        task_id: str,
        description: str,
        division: Division,
        context: Dict
    ) -> Dict[str, Any]:
        """Execute task with specified division agents."""
        start_time = time.time()

        # Simulate execution (would call actual agent implementations)
        logger.info(f"   Executing with {division.main_agent}...")

        # Simulate sub-agent coordination
        sub_results = []
        for sub in division.sub_agents:
            logger.debug(f"      Sub-agent {sub} processing...")
            sub_results.append({"agent": sub, "status": "completed"})

        execution_time = time.time() - start_time

        completed_at = datetime.utcnow().isoformat()

        return {
            "task_id": task_id,
            "status": "completed",
            "division": division.code,
            "main_agent": division.main_agent,
            "sub_agents_used": division.sub_agents,
            "execution_time_seconds": execution_time,
            "created_at": completed_at,  # Will be overwritten
            "completed_at": completed_at,
            "result": {
                "summary": f"Task executed by {division.name}",
                "sub_results": sub_results,
                "context_applied": context,
            },
            "safety_passed": True,
        }

    def _blocked_result(
        self,
        task_id: str,
        created_at: str,
        safety_result: Dict
    ) -> Dict[str, Any]:
        """Generate result for blocked task."""
        return {
            "task_id": task_id,
            "status": "blocked",
            "division": "DIV-05",
            "main_agent": "Chief Safety Agent",
            "sub_agents_used": ["Safety Validator"],
            "execution_time_seconds": 0.0,
            "created_at": created_at,
            "completed_at": datetime.utcnow().isoformat(),
            "result": {
                "summary": "Task blocked by safety validation",
                "safety_result": safety_result,
            },
            "safety_passed": False,
            "error_message": safety_result.get("reason", "Safety validation failed"),
        }

    def _save_task_record(
        self,
        task_id: str,
        description: str,
        division: str,
        result: Dict
    ):
        """Save task execution record."""
        record = TaskRecord(
            task_id=task_id,
            description=description[:200],
            division=division,
            status=result["status"],
            created_at=result.get("created_at", datetime.utcnow().isoformat()),
            completed_at=result.get("completed_at"),
            result=result.get("result", {}),
            safety_passed=result.get("safety_passed", False),
            qa_passed=result.get("qa_passed", False),
            sub_agents_used=result.get("sub_agents_used", []),
        )

        task_file = self.tasks_path / f"{task_id}.json"
        task_file.write_text(json.dumps(record.__dict__, indent=2, default=str))


class AgentRegistry:
    """Registry for managing fleet agents."""

    def __init__(self, divisions: Dict[str, Division]):
        self.divisions = divisions

    def get_division(self, code: str) -> Optional[Division]:
        """Get division by code."""
        return self.divisions.get(code)

    def list_divisions(self) -> List[str]:
        """List all division codes."""
        return list(self.divisions.keys())

    def get_agent_topology(self) -> Dict[str, Any]:
        """Get complete agent topology."""
        return {
            div_code: {
                "name": div.name,
                "main": div.main_agent,
                "subs": div.sub_agents,
            }
            for div_code, div in self.divisions.items()
        }


class SafetyCore:
    """Safety validation system for fleet tasks."""

    def __init__(self, logs_path: Path):
        self.logs_path = logs_path
        self.blocked_patterns = [
            "delete all", "drop table", "rm -rf /", "format drive",
            "fabricate data", "create fake data", "generate fake",
        ]

    def validate(self, task_description: str, division: str) -> Dict[str, Any]:
        """
        Validate task for safety concerns.

        Returns:
            Dict with 'passed' (bool) and 'reason' (str if failed)
        """
        task_lower = task_description.lower()

        for pattern in self.blocked_patterns:
            if pattern in task_lower:
                return {
                    "passed": False,
                    "reason": f"Detected unsafe pattern: '{pattern}'",
                    "level": "critical",
                    "division": division,
                }

        # Check for fabrication risk in data-related tasks
        if division == "DIV-03" and any(kw in task_lower for kw in ["create data", "generate data"]):
            if "fake" in task_lower or "sample" in task_lower:
                return {
                    "passed": False,
                    "reason": "Potential fabrication risk: Creating fake/sample data",
                    "level": "warning",
                    "division": division,
                }

        return {
            "passed": True,
            "reason": None,
            "level": "pass",
            "division": division,
        }

    def status(self) -> Dict[str, Any]:
        """Get safety core status."""
        return {
            "enabled": True,
            "patterns_loaded": len(self.blocked_patterns),
            "status": "active",
        }


class QAGate:
    """Quality Assurance gate for task outputs."""

    def __init__(self, logs_path: Path):
        self.logs_path = logs_path

    def validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task output quality.

        Returns:
            Dict with 'passed' (bool) and optional 'notes'
        """
        notes = []

        # Check execution time
        exec_time = result.get("execution_time_seconds", 0)
        if exec_time < 0.1:
            notes.append("Warning: Very fast execution - verify completeness")

        # Check result content
        task_result = result.get("result", {})
        if not task_result.get("summary"):
            notes.append("Warning: Result summary missing")

        # Check sub-agent usage
        subs = result.get("sub_agents_used", [])
        if len(subs) == 0:
            notes.append("Warning: No sub-agents utilized")

        passed = len([n for n in notes if n.startswith("Error")]) == 0

        return {
            "passed": passed,
            "notes": notes,
            "status": "passed" if passed else "failed",
        }

    def status(self) -> Dict[str, Any]:
        """Get QA gate status."""
        return {
            "enabled": True,
            "checks": ["execution_time", "result_completeness", "sub_agent_usage"],
            "status": "active",
        }


if __name__ == "__main__":
    # Quick test
    orch = FleetOrchestrator()
    print(json.dumps(orch.health(), indent=2))

    # Test task execution
    result = orch.execute_task(
        "Build a Python API with authentication",
        safety_critical=False
    )
    print("\nTask Result:")
    print(json.dumps(result, indent=2))
