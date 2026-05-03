"""
FleetOrchestratorClient - Bridge between Hermes Agent and Enterprise Agent Fleet.

Provides seamless integration with automatic retry, timeout handling, and
comprehensive error handling.
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
import uuid


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FleetError(Exception):
    """Base exception for fleet operations."""
    pass


class FleetConnectionError(FleetError):
    """Raised when cannot connect to fleet."""
    pass


class FleetTimeoutError(FleetError):
    """Raised when fleet operation times out."""
    pass


class FleetValidationError(FleetError):
    """Raised when task validation fails."""
    pass


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    ROUTING = "routing"
    RUNNING = "running"
    SAFETY_CHECK = "safety_check"
    QA_GATE = "qa_gate"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result from fleet task execution."""
    task_id: str
    status: TaskStatus
    division: Optional[str] = None
    main_agent: Optional[str] = None
    sub_agents_used: List[str] = None
    result_data: Dict[str, Any] = None
    safety_passed: bool = False
    qa_passed: bool = False
    execution_time_seconds: float = 0.0
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    route_reason: Optional[str] = None

    def __post_init__(self):
        if self.sub_agents_used is None:
            self.sub_agents_used = []
        if self.result_data is None:
            self.result_data = {}


@dataclass
class FleetHealth:
    """Fleet health status."""
    ready: bool
    main_agents_count: int
    sub_agents_count: int
    divisions: List[str]
    status: str
    version: str
    uptime_seconds: int


class FleetOrchestratorClient:
    """
    Client for interacting with Enterprise Agent Fleet.

    Provides high-level interface to:
    - Submit tasks for execution
    - Check task status
    - List recent tasks
    - Monitor fleet health

    Example:
        >>> client = FleetOrchestratorClient(fleet_path="~/enterprise_agent_fleet")
        >>> result = client.submit_task(
        ...     task_description="Build REST API for user management",
        ...     task_type="engineering",
        ...     dry_run=False
        ... )
        >>> print(f"Task {result.task_id} completed: {result.status}")
    """

    # Division mapping for task routing
    DIVISION_MAP = {
        "communications": "DIV-01",
        "engineering": "DIV-02",
        "data_science": "DIV-03",
        "data": "DIV-03",
        "content": "DIV-04",
        "documentation": "DIV-04",
        "safety": "DIV-05",
        "qa": "DIV-05",
        "rules": "DIV-05",
        "ui": "DIV-06",
        "ux": "DIV-06",
        "operations": "DIV-07",
        "automation": "DIV-07",
    }

    # Safety taxonomy mapping
    SAFETY_TAXONOMY = {
        "DIV-01": "web_search",
        "DIV-02": "backend_code",
        "DIV-03": "statistical_analysis",
        "DIV-04": "technical_writing",
        "DIV-05": "rule_compliance",
        "DIV-06": "ui_design",
        "DIV-07": "automation",
    }

    def __init__(
        self,
        fleet_path: Union[str, Path],
        timeout: int = 300,
        max_retries: int = 3,
        use_rtk: bool = True
    ):
        """
        Initialize FleetOrchestratorClient.

        Args:
            fleet_path: Path to enterprise_agent_fleet installation
            timeout: Maximum seconds to wait for task completion
            max_retries: Number of retries for transient failures
            use_rtk: Whether to use RTK wrapping for subprocess
        """
        self.fleet_path = Path(fleet_path).expanduser().resolve()
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_rtk = use_rtk and os.getenv("HERMES_RTK_WRAP") == "1"

        # Validate fleet path
        if not self.fleet_path.exists():
            raise FleetConnectionError(f"Fleet path does not exist: {self.fleet_path}")

        self._tasks_dir = self.fleet_path / "data" / "tasks"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized FleetOrchestratorClient at {self.fleet_path}")
        logger.info(f"RTK mode: {self.use_rtk}")

    def _run_fleet_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute fleet command with RTK support and retry logic.

        Args:
            command: Command and arguments as list
            cwd: Working directory
            timeout: Override default timeout

        Returns:
            JSON parsed result

        Raises:
            FleetConnectionError: When connection fails
            FleetTimeoutError: When operation times out
        """
        timeout = timeout or self.timeout
        work_dir = cwd or self.fleet_path

        # Build command with optional RTK wrapper
        if self.use_rtk:
            full_command = ["rtk", "run"] + command
        else:
            full_command = command

        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Running command (attempt {attempt + 1}): {' '.join(full_command)}")

                result = subprocess.run(
                    full_command,
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON output: {e}")
                        return {"success": True, "raw_output": result.stdout}
                else:
                    error_msg = result.stderr or result.stdout
                    logger.error(f"Command failed: {error_msg}")

                    # Check if it's a retryable error
                    if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.info(f"Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue

                    raise FleetConnectionError(f"Fleet command failed: {error_msg}")

            except subprocess.TimeoutExpired:
                last_error = FleetTimeoutError(f"Command timed out after {timeout}s")
                if attempt < self.max_retries - 1:
                    logger.warning(f"Timeout, retrying...")
                    continue
                raise last_error
            except Exception as e:
                last_error = FleetConnectionError(f"Command execution failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise last_error

        raise last_error or FleetConnectionError("Max retries exceeded")

    def _get_division(self, task_type: str) -> str:
        """Map task type to division code."""
        task_type_lower = task_type.lower()
        return self.DIVISION_MAP.get(task_type_lower, "DIV-07")  # Default to Operations

    def submit_task(
        self,
        task_description: str,
        task_type: str,
        dry_run: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """
        Submit a task to the fleet for execution.

        Args:
            task_description: Description of what needs to be done
            task_type: Type of task (engineering, data_science, content, etc.)
            dry_run: If True, only plan without execution
            context: Additional context (boss_id, priority, etc.)

        Returns:
            TaskResult with execution details

        Raises:
            FleetValidationError: When task validation fails
            FleetConnectionError: When fleet is unavailable
        """
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # Determine division
        division = self._get_division(task_type)

        logger.info(f"Submitting task {task_id} to {division} (dry_run={dry_run})")

        # Build task payload
        payload = {
            "task_id": task_id,
            "task_description": task_description,
            "task_type": task_type,
            "division": division,
            "dry_run": dry_run,
            "created_at": created_at,
            "context": context or {}
        }

        # Save task file
        task_file = self._tasks_dir / f"{task_id}.json"
        task_file.write_text(json.dumps(payload, indent=2))

        # Submit to fleet via CLI
        try:
            result = self._run_fleet_command(
                [
                    "python", "-m", "integrations.hermes_orchestrator",
                    "--task-id", task_id,
                    "--from-file", str(task_file)
                ]
            )
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                created_at=created_at
            )

        # Parse result
        return TaskResult(
            task_id=task_id,
            status=TaskStatus(result.get("status", "failed")),
            division=result.get("division"),
            main_agent=result.get("main_agent"),
            sub_agents_used=result.get("sub_agents_used", []),
            result_data=result.get("result", {}),
            safety_passed=result.get("safety_passed", False),
            qa_passed=result.get("qa_passed", False),
            execution_time_seconds=result.get("execution_time_seconds", 0),
            created_at=created_at,
            completed_at=result.get("completed_at"),
            error_message=result.get("error_message"),
            route_reason=result.get("route_reason")
        )

    def get_task_status(self, task_id: str) -> TaskResult:
        """
        Get current status of a task.

        Args:
            task_id: UUID of the task

        Returns:
            TaskResult with current status
        """
        task_file = self._tasks_dir / f"{task_id}.json"

        if not task_file.exists():
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="Task not found"
            )

        task_data = json.loads(task_file.read_text())
        result_file = self._tasks_dir / f"{task_id}_result.json"

        if result_file.exists():
            result_data = json.loads(result_file.read_text())
            task_data.update(result_data)

        return TaskResult(
            task_id=task_id,
            status=TaskStatus(task_data.get("status", "pending")),
            division=task_data.get("division"),
            main_agent=task_data.get("main_agent"),
            sub_agents_used=task_data.get("sub_agents_used", []),
            result_data=task_data.get("result", {}),
            safety_passed=task_data.get("safety_passed", False),
            qa_passed=task_data.get("qa_passed", False),
            execution_time_seconds=task_data.get("execution_time_seconds", 0),
            created_at=task_data.get("created_at"),
            completed_at=task_data.get("completed_at"),
            error_message=task_data.get("error_message")
        )

    def list_recent_tasks(self, limit: int = 10) -> List[TaskResult]:
        """
        List recent tasks from the fleet.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of TaskResult ordered by creation time (newest first)
        """
        tasks = []

        for task_file in sorted(
            self._tasks_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            # Skip result files
            if "_result" in task_file.name:
                continue

            task_id = task_file.stem
            tasks.append(self.get_task_status(task_id))

            if len(tasks) >= limit:
                break

        return tasks

    def fleet_status(self) -> FleetHealth:
        """
        Get current fleet health status.

        Returns:
            FleetHealth with readiness and topology info
        """
        try:
            result = self._run_fleet_command(
                ["python", "-m", "integrations.hermes_cli", "status"],
                timeout=10
            )

            return FleetHealth(
                ready=result.get("ready", False),
                main_agents_count=result.get("main_agents", 7),
                sub_agents_count=result.get("sub_agents", 21),
                divisions=result.get("divisions", []),
                status=result.get("status", "unknown"),
                version=result.get("version", "unknown"),
                uptime_seconds=result.get("uptime_seconds", 0)
            )
        except Exception as e:
            logger.error(f"Failed to get fleet status: {e}")
            return FleetHealth(
                ready=False,
                main_agents_count=0,
                sub_agents_count=0,
                divisions=[],
                status=f"error: {e}",
                version="unknown",
                uptime_seconds=0
            )

    def wait_for_task(
        self,
        task_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[int] = None
    ) -> TaskResult:
        """
        Wait for a task to complete with polling.

        Args:
            task_id: Task to wait for
            poll_interval: Seconds between status checks
            timeout: Override default timeout

        Returns:
            Final TaskResult

        Raises:
            FleetTimeoutError: When task doesn't complete in time
        """
        timeout = timeout or self.timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self.get_task_status(task_id)

            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED]:
                return result

            logger.debug(f"Task {task_id} status: {result.status.value}, waiting...")
            time.sleep(poll_interval)

        raise FleetTimeoutError(f"Task {task_id} did not complete within {timeout}s")


# Convenience function
def get_fleet_client(
    fleet_path: Optional[str] = None,
    **kwargs
) -> FleetOrchestratorClient:
    """
    Create fleet client with auto-discovery of fleet path.

    Args:
        fleet_path: Override fleet path. If None, tries common locations
        **kwargs: Additional arguments for FleetOrchestratorClient

    Returns:
        Configured FleetOrchestratorClient
    """
    if fleet_path is None:
        # Try common locations
        candidates = [
            Path.home() / "workspace" / "enterprise_agent_fleet",
            Path.home() / "enterprise_agent_fleet",
            Path("/opt/enterprise_agent_fleet"),
        ]
        for path in candidates:
            if path.exists():
                fleet_path = str(path)
                break

        if fleet_path is None:
            raise FleetConnectionError(
                "Could not auto-detect fleet path. Please specify fleet_path explicitly."
            )

    return FleetOrchestratorClient(fleet_path=fleet_path, **kwargs)


if __name__ == "__main__":
    # Quick test
    try:
        client = get_fleet_client()
        print(json.dumps(asdict(client.fleet_status()), indent=2))
    except Exception as e:
        print(f"Test failed: {e}")
        print("Note: This requires enterprise_agent_fleet to be installed")
