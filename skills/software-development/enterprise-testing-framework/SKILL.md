---
name: enterprise-testing-framework
description: Building comprehensive testing frameworks with mock utilities, scenario-based testing, and coverage reporting for enterprise agent systems
category: software-development
---

# Enterprise Testing Framework

Building isolated, comprehensive testing frameworks for complex enterprise systems with multiple integrated components.

## When to Use

- Creating test harnesses for multi-component systems (orchestrators, fleets, agent systems)
- Need isolated testing without full system initialization
- Require scenario-based test definitions with expected outcomes
- Need coverage reporting across divisions/modules

## Architecture Pattern

### 1. Test Harness Structure

```python
@dataclass
class ScenarioDefinition:
    name: str
    description: str
    task_description: str
    task_type: Optional[str]
    command: str
    dry_run: bool
    expected_safety_pass: bool
    expected_division: Optional[str] = None
    timeout_seconds: float = 30.0
```

### 2. Mock Utilities Pattern

Create isolated mocks for each major component:

```python
@dataclass
class MockTaskResult:
    task_id: str
    success: bool
    division: str
    agent: str
    safety_passed: bool
    output: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

class MockFleet:
    DIVISION_MAP = {
        "research": "DIV-01",
        "engineering": "DIV-02",
        # ...
    }
    
    def route_task(self, task_description: str, task_type: Optional[str] = None):
        # Auto-route based on keywords if no explicit type
        if not task_type:
            keywords_to_division = {
                "api": "DIV-02", "code": "DIV-02",
                "research": "DIV-01", "find": "DIV-01",
                # ...
            }
            # Match keywords...
```

### 3. Edge Case Test Categories

Always test these boundary conditions:

| Category | Examples |
|----------|----------|
| **Timeouts** | Tasks exceeding max execution time |
| **Partial Failures** | Some agents succeed, some fail |
| **Invalid Inputs** | Empty tasks, unknown types, oversized payloads |
| **Unicode/Special Chars** | Emoji, non-ASCII, control characters |
| **Injection Attempts** | SQL injection, XSS, command injection |
| **Resource Exhaustion** | Division unavailable, rate limiting |
| **Safety Bypass** | Obfuscated harmful content |

## Common Pitfalls & Solutions

### Pitfall 1: Relative Import Errors
```python
# ❌ Breaks when running as __main__
from .mock_utilities import MockHermes

# ✅ Use absolute imports for test files
from mock_utilities import MockHermes
```

### Pitfall 2: Dataclass vs Dict Confusion
```python
# ❌ Assuming dict return
report = analyzer.generate_report()
assert "timestamp" in report  # Fails if dataclass

# ✅ Check type explicitly
from coverage_report import CoverageReport
report = analyzer.generate_report()
assert isinstance(report, CoverageReport)
assert report.timestamp is not None
```

### Pitfall 3: Mixed-Type Aggregation
```python
# ❌ Crashes when summing mixed types
structure = {
    "divisions": {"eng": 5, "research": 3},  # dict
    "integrations": ["file1.py", "file2.py"],  # list
    "monitoring": 2,  # int
}
total = sum(len(v) if isinstance(v, list) else v for v in structure.values())
# TypeError: unsupported operand type(s) for +: 'int' and 'dict'

# ✅ Handle nested structures
sum(
    len(v) if isinstance(v, list) 
    else (sum(v.values()) if isinstance(v, dict) else v)
    for v in structure.values()
)
```

### Pitfall 4: Dataclass Attribute Access in Tests
```python
# ❌ May fail in complex import scenarios
result = fleet.route_task("test")
assert result.division == "DIV-02"

# ✅ Use hasattr check with informative errors
result = fleet.route_task("test")
assert hasattr(result, 'division'), f"Missing attr. Type: {type(result)}"
assert result.division == "DIV-02", f"Got: {result.division}"
```

### Pitfall 5: Class Variable Mutation Leaks Across Scenarios
```python
# ❌ Mutates class-level shared state (affects later tests)
mock.fleet.DIVISION_MAP.clear()

# ✅ Use instance-level copies inside __init__
class MockFleet:
    DIVISION_MAP = {"engineering": "DIV-02"}

    def __init__(self):
        self.DIVISION_MAP = dict(type(self).DIVISION_MAP)  # per-instance copy
```

### Pitfall 6: Pytest Collects Helper Classes as Tests
```python
# ❌ Named like a test helper but collected by pytest because it starts with Test
class TestHarness:
    def __init__(self):
        ...

# ✅ Mark helper classes as non-tests
class TestHarness:
    __test__ = False
    def __init__(self):
        ...
```

Use this when a helper class lives in a test module and pytest emits a collection warning.

### Pitfall 7: Cross-Test State Leakage from Class Variables
```python
# ❌ Mutates class-level shared state (affects later tests)
mock.fleet.DIVISION_MAP.clear()

# ✅ Copy shared maps into per-instance state in __init__
class MockFleet:
    DIVISION_MAP = {"engineering": "DIV-02"}

    def __init__(self):
        self.DIVISION_MAP = dict(type(self).DIVISION_MAP)
```

If one scenario needs to mutate routing maps (e.g. resource exhaustion), class-level dictionaries can poison later scenarios unless each instance gets its own copy.

### Pitfall 8: Add Deterministic QA Helpers Before Relying on Model Output
```python
class CompletenessValidator(SubAgentBase):
    def find_placeholders(self, deliverable: Any) -> List[Dict[str, str]]:
        ...

    def audit_local_completeness(self, deliverable: Any, requirements: List[str]) -> Dict[str, Any]:
        ...
```

For completeness/compliance tasks, add a local deterministic audit helper that can be tested directly. Then keep the model-powered `execute()` path as a wrapper around that core logic.

### Verification Pattern Observed
- Running `pytest tests/` initially exposed a collection INTERNALERROR from script-style tests.
- Fix: move top-level script logic into callable functions and keep `if __name__ == "__main__"` only for manual runs.
- After cleanup, the suite reached `31 passed` with no warnings.

### Phase 9 QA Hardening Notes
- Completeness checks should explicitly scan for placeholders such as `TODO`, `TBD`, `FIXME`, `example.com`, and `N/A`.
- When validating deliverable completeness, test both:
  - missing required components
  - placeholder detection
- Prefer deterministic completeness scoring in tests; treat model output as an integration wrapper, not the source of truth.

### Pitfall 6: Pytest INTERNALERROR from script-style test modules
```python
# ❌ Top-level execution in test module (runs during import/collection)
print("Running integration checks...")
results = run_checks()
sys.exit(0 if results.ok else 1)

# ✅ Keep side effects under __main__, expose pytest test functions

def run_checks():
    ...
    return results

def test_integration_checks_pass():
    results = run_checks()
    assert results.ok

if __name__ == "__main__":
    # Optional standalone runner for manual use
    results = run_checks()
    sys.exit(0 if results.ok else 1)
```

This prevents collection-time exits and fixes `pytest tests/` INTERNALERROR while preserving a direct script mode for manual execution.

## Implementation Steps

1. **Define TestResult dataclass** - Standardize result structure
2. **Create Mock Component Classes** - One per major system component
3. **Build TestHarness** - Scenario runner with lifecycle management
4. **Implement EdgeCaseTestSuite** - Predefined boundary condition tests
5. **Add CoverageAnalyzer** - Track division/agent coverage, generate reports
6. **Write Integration Tests** - Validate the testing framework itself

## Coverage Report Structure

```python
@dataclass
class CoverageReport:
    timestamp: str
    test_summary: Dict[str, Any]
    code_coverage: Dict[str, Any]
    division_coverage: Dict[str, Any]
    safety_coverage: Dict[str, Any]
    integration_coverage: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
```

## Key Metrics to Track

- **Division Coverage**: % of divisions tested
- **Safety Interactions**: Pass/block/error counts
- **Performance**: Min/max/avg response times
- **Edge Cases**: Timeout, injection, resource exhaustion coverage

## Example Usage

```python
from testing.test_harness import TestHarness
from testing.edge_case_tests import EdgeCaseTestSuite
from testing.coverage_report import CoverageAnalyzer

# Run scenarios
harness = TestHarness()
report = harness.run_all()

# Run edge cases
suite = EdgeCaseTestSuite()
edge_results = suite.run_all()

# Generate coverage report
analyzer = CoverageAnalyzer()
coverage = analyzer.generate_report(
    test_results=report['results'] + edge_results['results']
)
output_path = analyzer.save_report(coverage)
```

## Debugging Tips

1. **Always test mocks in isolation first** - Run simple cases before complex scenarios
2. **Print MRO for type confusion** - `print(type(result).__mro__)`
3. **Use dataclass.fields() for field verification** - `fields(MockTaskResult)`
4. **Test empty inputs explicitly** - Many bugs appear with empty lists/dicts
5. **Verify import paths** - Use `sys.path.insert(0, 'testing')` consistently
6. **Add deterministic audit helpers for completeness/placeholder checks** - Keep a local, model-free precheck for simple validity signals (missing sections, TODO/TBD, example.com) so QA tests can assert behavior without relying on LLM output