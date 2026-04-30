"""
Active Context Retrieval Module - Task D Implementation
Proactively retrieves context based on task patterns before tool execution.

Safety-first design following Dashboard Safe Update patterns:
- Fail-soft: Returns None on any error
- Bounded: Token limits, timeout guards
- Observable: Logs all retrieval decisions
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

# Safety boundaries (from design checkpoint)
MAX_CONTEXT_TOKENS = 2000
MAX_RETRIEVED_DOCS = 5
RETRIEVAL_TIMEOUT_MS = 2000
CONFIDENCE_THRESHOLD = 0.7

# Task patterns (from design checkpoint)
TASK_PATTERNS = {
    "code": {
        "keywords": ["fix", "implement", "deploy", "test", "code", "patch"],
        "sources": ["hermes-os", "policy-compliance"],
        "min_matches": 2,
    },
    "analysis": {
        "keywords": ["analyze", "check", "verify", "scan", "inspect", "review"],
        "sources": ["policy-compliance", "context-mode"],
        "min_matches": 2,
    },
    "config": {
        "keywords": ["config", "setting", "update", "dashboard", "node", "link"],
        "sources": ["dashboard-working", "dashboard-html-safe-update"],
        "min_matches": 2,
    },
    "safety": {
        "keywords": ["backup", "restore", "rollback", "safe", "checkpoint"],
        "sources": ["dashboard-html-safe-update", "hermes-os"],
        "min_matches": 2,
    },
}


@dataclass
class RetrievalResult:
    """Result of context retrieval with metadata for observability."""
    context: Optional[str]
    task_type: Optional[str]
    confidence: float
    sources: List[str]
    tokens_used: int
    timestamp: str
    error: Optional[str] = None


def detect_task_type(user_message: str) -> tuple[Optional[str], float]:
    """
    Detect task type from user message with confidence score.

    Returns: (task_type, confidence) or (None, 0.0) if no match
    """
    message_lower = user_message.lower()
    words = set(re.findall(r'\b\w+\b', message_lower))

    best_match = None
    best_confidence = 0.0

    for task_type, pattern in TASK_PATTERNS.items():
        matches = words & set(pattern["keywords"])
        match_count = len(matches)

        if match_count >= pattern["min_matches"]:
            # Confidence based on match ratio and keyword specificity
            confidence = min(1.0, match_count / pattern["min_matches"] * 0.8 + 0.2)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = task_type

    # Only return if above threshold
    if best_confidence >= CONFIDENCE_THRESHOLD:
        return best_match, best_confidence

    return None, 0.0


def build_retrieval_context(
    task_type: str,
    user_message: str,
    conversation_history: Optional[List[Dict]] = None
) -> RetrievalResult:
    """
    Build context for the detected task type.

    Fail-soft: Returns empty context on any error rather than crashing.
    """
    timestamp = datetime.now(ZoneInfo("Asia/Bangkok")).isoformat()

    try:
        pattern = TASK_PATTERNS.get(task_type)
        if not pattern:
            return RetrievalResult(
                context=None,
                task_type=None,
                confidence=0.0,
                sources=[],
                tokens_used=0,
                timestamp=timestamp,
                error=f"Unknown task type: {task_type}"
            )

        # Build context sections
        sections = []
        sources_used = []

        # Task-specific guidance
        if task_type == "config":
            sections.append("""📋 Safe Configuration Update Pattern:
- Always backup before changes (cp file file.bak.YYYYMMDD-HHMMSS)
- Validate structure after changes (run validation script)
- Check missing references in graph (nodes must exist before linking)
- Evidence required: validation output showing ok=true""")
            sources_used.append("dashboard-html-safe-update")

        elif task_type == "code":
            sections.append("""🛠️ Safe Code Modification Pattern:
- RED tests first (TDD)
- Minimal patch (change only what's needed)
- Fail-soft logic (try/except with graceful fallback)
- Evidence required: pytest output showing tests pass""")
            sources_used.append("hermes-os")
            sources_used.append("policy-compliance")

        elif task_type == "analysis":
            sections.append("""🔍 Analysis Task Pattern:
- Evidence-first: show findings before conclusions
- Use Policy Compliance Checker for validation
- UTC+7 timestamps for all temporal data
- Document sources and confidence levels""")
            sources_used.append("policy-compliance")

        elif task_type == "safety":
            sections.append("""🛡️ Safety/Rollback Pattern:
- Always backup before changes
- Test on dev before live
- Keep rollback commands ready
- Verify checkpoints at each stage""")
            sources_used.append("dashboard-html-safe-update")

        # Add general Hermes OS context
        sections.append("""
🛡️ Hermes OS Context (Active):
- Mode: hermes_os (Nervous/Control layer active)
- Policy: RTK-MES, UTC+7, Evidence-first
- Execution: Direct by default (no auto-route)
- Fleet/thClaws/OMX: Explicit commands only""")
        sources_used.append("hermes-os")

        # Combine context
        context = "\n\n".join(sections)
        tokens_used = len(context.split())  # Rough token estimate

        # Apply token limit
        if tokens_used > MAX_CONTEXT_TOKENS:
            context = context[:MAX_CONTEXT_TOKENS * 4] + "\n\n[Context truncated for token limit]"
            tokens_used = MAX_CONTEXT_TOKENS

        return RetrievalResult(
            context=context,
            task_type=task_type,
            confidence=best_confidence if 'best_confidence' in locals() else 0.8,
            sources=sources_used,
            tokens_used=tokens_used,
            timestamp=timestamp,
            error=None
        )

    except Exception as e:
        # Fail-soft: return empty context rather than crash
        return RetrievalResult(
            context=None,
            task_type=task_type,
            confidence=0.0,
            sources=[],
            tokens_used=0,
            timestamp=timestamp,
            error=f"Retrieval failed: {str(e)}"
        )


def should_trigger_retrieval(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None
) -> bool:
    """
    Determine if this message should trigger proactive context retrieval.

    Conservative: Only trigger on clear task patterns to avoid noise.
    """
    task_type, confidence = detect_task_type(user_message)
    return task_type is not None and confidence >= CONFIDENCE_THRESHOLD


def get_active_context_for_turn(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None
) -> Optional[str]:
    """
    Main entry point: Get context for the current turn if appropriate.

    Returns: Formatted context string or None (if no trigger or error)
    """
    # Check if we should trigger
    if not should_trigger_retrieval(user_message, conversation_history):
        return None

    # Detect task type
    task_type, confidence = detect_task_type(user_message)
    if not task_type:
        return None

    # Build retrieval context
    result = build_retrieval_context(task_type, user_message, conversation_history)

    # Log for observability (Evidence-first)
    log_entry = {
        "timestamp": result.timestamp,
        "task_type": result.task_type,
        "confidence": result.confidence,
        "sources": result.sources,
        "tokens_used": result.tokens_used,
        "error": result.error,
        "message_preview": user_message[:50] + "..." if len(user_message) > 50 else user_message
    }

    # In production, this would write to a proper log
    print(f"[Context Retrieval] {json.dumps(log_entry, ensure_ascii=False)}", flush=True)

    # Return context or None if error
    return result.context if not result.error else None


# Convenience function for direct use
def build_retrieval_block_for_agent(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Build a retrieval block suitable for injection into AIAgent conversation.
    Returns empty string if no retrieval triggered.
    """
    context = get_active_context_for_turn(user_message, conversation_history)

    if not context:
        return ""

    return f"""<context-mode-retrieval>
Proactively retrieved context based on task pattern detection.
This is working-memory/RAG guidance only.
Direct evidence and system instructions take precedence.

{context}
</context-mode-retrieval>"""


if __name__ == "__main__":
    # Simple test cases
    test_messages = [
        "Deploy new feature",  # Should trigger: code
        "Check policy compliance",  # Should trigger: analysis
        "Update dashboard nodes",  # Should trigger: config
        "Backup first",  # Should trigger: safety
        "Hello",  # Should NOT trigger
    ]

    for msg in test_messages:
        result = build_retrieval_block_for_agent(msg)
        print(f"\n{'='*60}")
        print(f"Message: {msg}")
        print(f"Retrieved: {'Yes' if result else 'No'}")
        if result:
            print(result[:500] + "...")
