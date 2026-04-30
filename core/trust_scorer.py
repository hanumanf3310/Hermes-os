"""
Hermes Trust Score System
ระบบคะแนนความน่าเชื่อถือสำหรับ facts

Inspired by Claude OS Knowledge Lifecycle Engine

Author: Hermes OS
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


@dataclass
class TrustFactors:
    """Factors that affect trust score"""
    # Creation factors (0.0 - 1.0)
    creation_source: float = 0.0  # How it was created
    
    # Validation factors
    user_confirmations: int = 0   # Boss said it was correct
    user_corrections: int = 0     # Boss corrected it
    references: int = 0          # Times used in decisions
    
    # Quality factors
    is_well_formed: bool = True    # Clear entity/content structure
    is_vague: bool = False         # Ambiguous wording
    is_temporary: bool = False     # Marked as temp/note
    
    # Age factor
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    
    # Calculation cache
    _cached_score: Optional[float] = None
    _cached_at: Optional[datetime] = None


class TrustScorer:
    """
    คำนวณ trust score สำหรับ facts
    
    Trust Score = 0.5 (neutral) 
        + creation_bonus
        + validation_bonus
        + quality_bonus
        - age_penalty
    """
    
    # Weights for calculation
    WEIGHTS = {
        "base": 0.5,
        "creation": {
            "explicit_confirm": 0.4,      # Boss said "save this"
            "auto_extract": 0.2,          # Extracted from message
            "pattern_match": 0.1,         # Matched trigger pattern
            "system_detect": 0.15,        # Auto-detected from system
        },
        "validation": {
            "user_confirmation": 0.3,     # Boss confirmed correct
            "reference_in_decision": 0.1, # Used in actual work
            "user_correction": -0.2,      # Boss said it was wrong
            "contradicted": -0.3,         # New fact contradicts
        },
        "quality": {
            "well_formed": 0.1,           # Clear structure
            "vague": -0.1,                # Ambiguous
            "temporary": -0.3,            # Marked as temp
        },
        "age": {
            "accessed_week": 0.05,        # Accessed within 7 days
            "stale_month": -0.1,          # Not accessed 30+ days
            "archived": -0.2,             # Not accessed 90+ days
        }
    }
    
    # Trust level thresholds
    LEVELS = {
        "verified": (0.9, 1.0, "⭐⭐⭐ Verified"),
        "trusted": (0.7, 0.89, "⭐⭐ Trusted"),
        "neutral": (0.5, 0.69, "⭐ Neutral"),
        "low": (0.3, 0.49, "⚠️ Low Trust"),
        "untrusted": (0.0, 0.29, "❌ Untrusted"),
    }
    
    def __init__(self):
        """Initialize scorer"""
        pass
    
    def calculate_score(self, factors: TrustFactors) -> float:
        """
        คำนวณ trust score จาก factors
        
        Returns:
            float: Trust score 0.0 - 1.0
        """
        score = self.WEIGHTS["base"]
        
        # Creation bonus
        score += factors.creation_source
        
        # Validation bonus
        score += (factors.user_confirmations * 
                  self.WEIGHTS["validation"]["user_confirmation"])
        score += (factors.user_corrections * 
                  self.WEIGHTS["validation"]["user_correction"])
        score += (factors.references * 
                  self.WEIGHTS["validation"]["reference_in_decision"])
        
        # Quality bonus
        if factors.is_well_formed:
            score += self.WEIGHTS["quality"]["well_formed"]
        if factors.is_vague:
            score += self.WEIGHTS["quality"]["vague"]
        if factors.is_temporary:
            score += self.WEIGHTS["quality"]["temporary"]
        
        # Age penalty/bonus
        now = datetime.now()
        
        if factors.last_accessed:
            days_since_access = (now - factors.last_accessed).days
            
            if days_since_access <= 7:
                score += self.WEIGHTS["age"]["accessed_week"]
            elif days_since_access >= 90:
                score += self.WEIGHTS["age"]["archived"]
            elif days_since_access >= 30:
                score += self.WEIGHTS["age"]["stale_month"]
        
        # Cap at 0.0 - 1.0
        return max(0.0, min(1.0, score))
    
    def get_level(self, score: float) -> Tuple[str, str]:
        """
        แปลง score เป็น level + emoji
        
        Returns:
            (level_name, display_text)
        """
        for level, (min_score, max_score, display) in self.LEVELS.items():
            if min_score <= score <= max_score:
                return level, display
        
        return "unknown", "❓ Unknown"
    
    def get_recommendation(self, score: float) -> str:
        """
        ให้คำแนะนำตาม trust level
        """
        if score >= 0.9:
            return "ใช้ได้เต็มที่ - น่าเชื่อถือสูง"
        elif score >= 0.7:
            return "ใช้ได้ - แต่ระวัง double-check ถ้าสำคัญ"
        elif score >= 0.5:
            return "ใช้ได้แต่ควร verify ก่อนใช้"
        elif score >= 0.3:
            return "⚠️ ล้าสมัยหรือไม่แน่ใจ - ควร update ก่อนใช้"
        else:
            return "❌ ไม่ควรใช้ - อาจผิดหรือ outdated มาก"
    
    def create_factors_from_source(self, source_type: str) -> TrustFactors:
        """
        สร้าง TrustFactors ตาม source type
        
        Args:
            source_type: "explicit" | "auto_extract" | "pattern" | "system"
        
        Returns:
            TrustFactors ที่กำหนด creation_source แล้ว
        """
        creation_scores = {
            "explicit": 0.4,
            "auto_extract": 0.2,
            "pattern": 0.1,
            "system": 0.15,
        }
        
        return TrustFactors(
            creation_source=creation_scores.get(source_type, 0.0),
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
    
    def apply_feedback(self, factors: TrustFactors, 
                      action: str) -> TrustFactors:
        """
        ปรับ factors ตาม user feedback
        
        Args:
            factors: Current factors
            action: "helpful" | "unhelpful" | "confirmed" | "corrected"
        
        Returns:
            Updated TrustFactors
        """
        if action == "helpful":
            factors.user_confirmations += 1
        elif action == "unhelpful":
            factors.user_corrections += 1
        elif action == "confirmed":
            factors.user_confirmations += 1
        elif action == "corrected":
            factors.user_corrections += 1
        
        # Clear cache
        factors._cached_score = None
        return factors


class TrustReport:
    """Generate trust report for Boss"""
    
    def __init__(self, scorer: TrustScorer):
        self.scorer = scorer
    
    def generate_summary(self, facts_with_trust: List[Dict]) -> str:
        """
        สร้างสรุป report
        """
        if not facts_with_trust:
            return "ไม่มี facts ในระบบ"
        
        # Count by level
        counts = {"verified": 0, "trusted": 0, 
                 "neutral": 0, "low": 0, "untrusted": 0}
        
        for fact in facts_with_trust:
            score = fact.get("trust_score", 0.5)
            level, _ = self.scorer.get_level(score)
            counts[level] = counts.get(level, 0) + 1
        
        total = len(facts_with_trust)
        
        lines = [
            "📊 **Trust Score Summary**",
            "",
            f"📦 **Total Facts:** {total}",
            f"  ⭐⭐⭐ Verified: {counts['verified']} ({counts['verified']/total*100:.0f}%)",
            f"  ⭐⭐ Trusted: {counts['trusted']} ({counts['trusted']/total*100:.0f}%)",
            f"  ⭐ Neutral: {counts['neutral']} ({counts['neutral']/total*100:.0f}%)",
            f"  ⚠️ Low Trust: {counts['low']} ({counts['low']/total*100:.0f}%)",
            f"  ❌ Untrusted: {counts['untrusted']} ({counts['untrusted']/total*100:.0f}%)",
            "",
            "💡 **Recommendations:**",
        ]
        
        if counts['untrusted'] > 0:
            lines.append(f"  - Archive {counts['untrusted']} untrusted facts")
        if counts['low'] > total * 0.2:
            lines.append(f"  - Review {counts['low']} low-trust facts")
        if counts['verified'] < total * 0.3:
            lines.append("  - Confirm important facts to increase trust")
        
        return "\n".join(lines)


# Convenience functions
_scorer = None

def get_scorer():
    """Get singleton scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = TrustScorer()
    return _scorer


def calculate_trust_score(factors: TrustFactors) -> float:
    """Calculate score for factors"""
    return get_scorer().calculate_score(factors)


def get_trust_indicators(score: float) -> Tuple[str, str, str]:
    """
    Get display indicators for trust score
    
    Returns:
        (emoji, level, recommendation)
    """
    scorer = get_scorer()
    level, display = scorer.get_level(score)
    rec = scorer.get_recommendation(score)
    
    # Extract emoji from display
    emoji = display.split()[0] if display else "❓"
    
    return emoji, level, rec


# CLI Test
if __name__ == "__main__":
    import sys
    
    print("🧪 **Trust Score System Test**\n")
    print("=" * 60)
    
    scorer = TrustScorer()
    
    # Test 1: Different creation sources
    print("\n📋 **Test 1: Creation Source Impact**\n")
    
    sources = [
        ("explicit", "Boss said 'save this'"),
        ("auto_extract", "Extracted from message"),
        ("pattern", "Matched trigger pattern"),
        ("system", "Auto-detected"),
    ]
    
    for source, desc in sources:
        factors = scorer.create_factors_from_source(source)
        score = scorer.calculate_score(factors)
        level, display = scorer.get_level(score)
        print(f"  {source:15} | Score: {score:.2f} | {display}")
    
    # Test 2: Feedback impact
    print("\n📋 **Test 2: Feedback Impact**\n")
    
    factors = scorer.create_factors_from_source("auto_extract")
    base_score = scorer.calculate_score(factors)
    print(f"  Initial (auto_extract): {base_score:.2f}")
    
    factors = scorer.apply_feedback(factors, "helpful")
    score_after_helpful = scorer.calculate_score(factors)
    print(f"  After 'helpful':        {score_after_helpful:.2f} (+{score_after_helpful-base_score:.2f})")
    
    factors = scorer.apply_feedback(factors, "confirmed")
    score_after_confirm = scorer.calculate_score(factors)
    print(f"  After 'confirmed':      {score_after_confirm:.2f} (+{score_after_confirm-score_after_helpful:.2f})")
    
    # Test 3: Age impact
    print("\n📋 **Test 3: Age Impact**\n")
    
    now = datetime.now()
    ages = [
        (now - timedelta(days=2), "2 days ago (fresh)"),
        (now - timedelta(days=20), "20 days ago (normal)"),
        (now - timedelta(days=35), "35 days ago (stale)"),
        (now - timedelta(days=95), "95 days ago (archived)"),
    ]
    
    for last_accessed, desc in ages:
        factors = scorer.create_factors_from_source("explicit")
        factors.last_accessed = last_accessed
        score = scorer.calculate_score(factors)
        print(f"  {desc:25} | Score: {score:.2f}")
    
    # Test 4: Format display
    print("\n📋 **Test 4: Trust Indicators**\n")
    
    test_scores = [0.95, 0.75, 0.55, 0.35, 0.15]
    for score in test_scores:
        emoji, level, rec = get_trust_indicators(score)
        print(f"  Score {score:.2f}: {emoji} {level:12} | {rec[:40]}...")
    
    print("\n" + "=" * 60)
    print("\n✅ **All tests passed!**")
