"""
Hermes OS Core Memory Enhancement Modules
Integrates Trust Score, Feedback Loop, and Session State

Author: Hermes OS
"""

from .trust_scorer import TrustScorer, TrustFactors, get_scorer, get_trust_indicators
from .fact_feedback import FactFeedback
from .trust_display import TrustDisplay
from .session_state import SessionManager, SessionState
from .category_detector import CategoryDetector, auto_detect_category
from .hermes_os_memory import HermesMemorySystem, get_memory_system, on_hermes_startup

__all__ = [
    "TrustScorer",
    "TrustFactors",
    "get_scorer",
    "get_trust_indicators",
    "FactFeedback",
    "TrustDisplay",
    "SessionManager",
    "SessionState",
    "CategoryDetector",
    "auto_detect_category",
    "HermesMemorySystem",
    "get_memory_system",
    "on_hermes_startup",
]

__version__ = "2.0.0"
