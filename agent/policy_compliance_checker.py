"""
Policy Compliance Checker for Hermes OS
Analyzes code against merged-hard-gate-policy.yaml
READ-ONLY: Never modifies target files
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


# Policy file location - check multiple paths
POLICY_FILE_PATHS = [
    Path.home() / ".hermes" / "website" / "docs" / "reference" / "merged-hard-gate-policy.yaml",
    Path.home() / "hermes-agent" / "website" / "docs" / "reference" / "merged-hard-gate-policy.yaml",
]


def _get_policy_file() -> Optional[Path]:
    """Find the policy file in available locations."""
    for path in POLICY_FILE_PATHS:
        if path.exists():
            return path
    return None


def check_compliance(file_path: str) -> Dict[str, Any]:
    """
    Check if a Python file complies with Hermes OS Policy Gateway rules.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        dict with status, violations, compliant patterns, and report
    """
    # Check policy file exists
    policy_file = _get_policy_file()
    if not policy_file:
        return {
            'status': 'error',
            'message': f'Policy file not found. Searched: {[str(p) for p in POLICY_FILE_PATHS]}',
            'violations': [],
            'compliant_patterns': [],
            'recommendations': []
        }
    
    # Check target file exists
    if not os.path.exists(file_path):
        return {
            'status': 'error',
            'message': f'Target file not found: {file_path}',
            'violations': [],
            'compliant_patterns': [],
            'recommendations': []
        }
    
    try:
        # Read policy file (safe, read-only)
        policy_content = policy_file.read_text(encoding='utf-8')
        policy_rules = _parse_policy(policy_content)
        
        # Read target file (safe, read-only)
        target_content = Path(file_path).read_text(encoding='utf-8')
        
        # Analyze compliance
        violations = []
        compliant_patterns = []
        
        # Check RTK compliance
        rtk_violations = _check_rtk_compliance(target_content)
        if rtk_violations:
            violations.extend(rtk_violations)
        else:
            if 'rtk run' in target_content:
                compliant_patterns.append('Uses rtk run pattern for terminal commands')
        
        # Check UTC-7 compliance (datetime patterns)
        utc7_violations = _check_utc7_compliance(target_content)
        if utc7_violations:
            violations.extend(utc7_violations)
        else:
            if 'Asia/Bangkok' in target_content or 'ZoneInfo' in target_content:
                compliant_patterns.append('Uses Asia/Bangkok timezone normalization')
        
        # Check Evidence-first patterns
        if _has_evidence_first_pattern(target_content):
            compliant_patterns.append('Follows evidence-first pattern (✅)')
        
        # Generate recommendations
        recommendations = _generate_recommendations(violations)
        
        # Build findings dict
        findings = {
            'violations': violations,
            'compliant_patterns': compliant_patterns,
            'recommendations': recommendations
        }
        
        # Generate report
        report = _generate_report(file_path, findings)
        
        return {
            'status': 'success',
            'message': f'Analysis complete for {file_path}',
            'violations': violations,
            'compliant_patterns': compliant_patterns,
            'recommendations': recommendations,
            'report': report
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Analysis failed: {str(e)}',
            'violations': [],
            'compliant_patterns': [],
            'recommendations': []
        }


def _parse_policy(policy_content: str) -> Dict[str, Any]:
    """Parse policy YAML content (simplified)."""
    rules = {
        'rtk_required': True,
        'utc7_required': True,
        'evidence_first': True
    }
    return rules


def _check_rtk_compliance(code: str) -> List[str]:
    """
    Check if terminal() calls use rtk run pattern.
    Returns list of violations found.
    """
    violations = []
    
    # Pattern: terminal("...") without rtk
    terminal_pattern = r'terminal\s*\(\s*["\']([^"\']+)["\']\s*\)'
    
    for match in re.finditer(terminal_pattern, code):
        line_num = code[:match.start()].count('\n') + 1
        cmd = match.group(1)
        
        # Check if rtk run is used
        if not cmd.strip().startswith('rtk'):
            # Check context - might be wrapped in rtk run
            context_start = max(0, match.start() - 200)
            context = code[context_start:match.start()]
            
            if 'rtk run' not in context:
                violations.append(
                    f'Line {line_num}: terminal() without rtk run wrapper: "{cmd[:50]}..."'
                )
    
    return violations


def _check_utc7_compliance(code: str) -> List[str]:
    """
    Check for UTC-7 / Asia/Bangkok timezone compliance.
    """
    violations = []
    
    # Look for datetime.now() without timezone
    naive_datetime_pattern = r'datetime\.now\s*\(\s*\)'
    
    for match in re.finditer(naive_datetime_pattern, code):
        line_num = code[:match.start()].count('\n') + 1
        
        # Check if surrounded by ZoneInfo or timezone context
        context_start = max(0, match.start() - 100)
        context = code[context_start:match.start()]
        
        if 'ZoneInfo' not in context and 'Asia/Bangkok' not in code:
            violations.append(
                f'Line {line_num}: datetime.now() without timezone normalization'
            )
    
    return violations


def _has_evidence_first_pattern(code: str) -> bool:
    """
    Check if code follows evidence-first pattern.
    """
    # Look for evidence markers
    evidence_markers = [
        'evidence:', 'evidence-first', '✅', 
        'ผลลัพธ์:', 'result:', 'หลักฐาน:'
    ]
    
    return any(marker in code for marker in evidence_markers)


def _generate_recommendations(violations: List[str]) -> List[str]:
    """Generate recommendations based on violations."""
    recommendations = []
    
    for v in violations:
        if 'rtk' in v.lower():
            recommendations.append('Wrap terminal commands with rtk run "..."')
        if 'timezone' in v.lower() or 'datetime' in v.lower():
            recommendations.append('Use datetime.now(ZoneInfo("Asia/Bangkok")) for UTC+7')
    
    if not recommendations:
        recommendations.append('All checks passed! No recommendations needed.')
    
    return recommendations


def _generate_report(file_path: str, findings: Dict[str, List[str]]) -> str:
    """
    Generate a human-readable compliance report.
    
    Args:
        file_path: Path to analyzed file
        findings: Dict with violations, compliant_patterns, recommendations
        
    Returns:
        Formatted report string
    """
    lines = [
        "=" * 50,
        "🛡️ Policy Compliance Report",
        "=" * 50,
        f"File: {file_path}",
        f"Policy: Hermes OS Policy Gateway",
        "-" * 50,
        ""
    ]
    
    # Violations section
    violations = findings.get('violations', [])
    if violations:
        lines.append("❌ Violations Found:")
        for v in violations:
            lines.append(f"   • {v}")
        lines.append("")
    else:
        lines.append("✅ No violations found!")
        lines.append("")
    
    # Compliant patterns
    compliant = findings.get('compliant_patterns', [])
    if compliant:
        lines.append("✅ Compliant Patterns:")
        for c in compliant:
            lines.append(f"   • {c}")
        lines.append("")
    
    # Recommendations
    recommendations = findings.get('recommendations', [])
    if recommendations:
        lines.append("💡 Recommendations:")
        for r in recommendations:
            lines.append(f"   → {r}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("End of Report")
    
    return "\n".join(lines)


# Convenience function for direct usage
def quick_check(file_path: str) -> str:
    """
    Quick check returning just the report string.
    Safe wrapper for CLI usage.
    """
    result = check_compliance(file_path)
    if result['status'] == 'error':
        return f"Error: {result['message']}"
    return result.get('report', 'No report generated')
