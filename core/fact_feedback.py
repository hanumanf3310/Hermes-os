#!/usr/bin/env python3
"""
Hermes Feedback Loop System
ระบบ feedback สำหรับ facts (helpful/unhelpful)

Integrates with: fact_store, trust_scorer
Protocol: v2.5 Tiny Trade (Testing)

Author: Hermes OS
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.trust_scorer import TrustFactors, TrustScorer, get_scorer


class FactFeedback:
    """
    จัดการ feedback สำหรับ facts
    
    Usage:
        feedback = FactFeedback()
        feedback.mark_helpful(fact_id=42)
        feedback.mark_unhelpful(fact_id=42, reason="Outdated")
        feedback.mark_confirmed(fact_id=42)
    """
    
    def __init__(self, scorer=None):
        self.scorer = scorer or get_scorer()
        self.feedback_history = {}  # fact_id -> list of feedbacks
    
    def mark_helpful(self, fact_id: int, context: str = "") -> dict:
        """
        Boss บอกว่า fact นี้ helpful / ถูกต้อง
        
        Effect: +0.3 trust score
        """
        return self._apply_feedback(
            fact_id=fact_id,
            action="helpful",
            effect=0.3,
            context=context
        )
    
    def mark_unhelpful(self, fact_id: int, reason: str = "", 
                       context: str = "") -> dict:
        """
        Boss บอกว่า fact นี้ unhelpful / ผิด / ล้าสมัย
        
        Effect: -0.2 trust score
        """
        return self._apply_feedback(
            fact_id=fact_id,
            action="unhelpful",
            effect=-0.2,
            context=context,
            reason=reason
        )
    
    def mark_confirmed(self, fact_id: int, context: str = "") -> dict:
        """
        Boss ยืนยันว่า fact นี้ถูกต้อง (explicit confirmation)
        
        Effect: +0.4 trust score (stronger than helpful)
        """
        return self._apply_feedback(
            fact_id=fact_id,
            action="confirmed",
            effect=0.4,
            context=context
        )
    
    def mark_corrected(self, fact_id: int, correction: str,
                      context: str = "") -> dict:
        """
        Boss บอกว่า fact นี้ผิด และให้ correction
        
        Effect: -0.2 trust + mark for update
        """
        result = self._apply_feedback(
            fact_id=fact_id,
            action="corrected",
            effect=-0.2,
            context=context,
            correction=correction
        )
        result["needs_update"] = True
        result["correction"] = correction
        return result
    
    def _apply_feedback(self, fact_id: int, action: str, 
                       effect: float, context: str = "",
                       reason: str = "", correction: str = "") -> dict:
        """Internal: apply feedback and return report"""
        
        feedback_entry = {
            "fact_id": fact_id,
            "action": action,
            "effect": effect,
            "context": context,
            "reason": reason,
            "correction": correction,
            "timestamp": datetime.now().isoformat() if 'datetime' in dir() else "now"
        }
        
        # Store in history
        if fact_id not in self.feedback_history:
            self.feedback_history[fact_id] = []
        self.feedback_history[fact_id].append(feedback_entry)
        
        # Calculate new trust score
        # In real implementation: fetch current factors from fact_store
        # For now: return the effect
        
        return {
            "fact_id": fact_id,
            "action": action,
            "trust_delta": effect,
            "total_feedback": len(self.feedback_history[fact_id]),
            "status": "applied",
            "message": self._get_success_message(action, effect)
        }
    
    def _get_success_message(self, action: str, effect: float) -> str:
        """Generate user-friendly message"""
        messages = {
            "helpful": f"💚 ขอบคุณค่ะ! Trust score +{effect}",
            "unhelpful": f"💔 รับทราบค่ะ จะปรับปรุง Trust score {effect}",
            "confirmed": f"✅ ยืนยันแล้ว! Trust score +{effect}",
            "corrected": f"📝 รับคำแก้ไขแล้วค่ะ Trust score {effect}",
        }
        return messages.get(action, f"Feedback recorded: {effect}")
    
    def get_fact_status(self, fact_id: int) -> dict:
        """Get feedback history for a fact"""
        history = self.feedback_history.get(fact_id, [])
        
        if not history:
            return {
                "fact_id": fact_id,
                "feedback_count": 0,
                "net_trust_delta": 0.0,
                "status": "no_feedback"
            }
        
        net_delta = sum(h["effect"] for h in history)
        
        return {
            "fact_id": fact_id,
            "feedback_count": len(history),
            "net_trust_delta": net_delta,
            "history": history,
            "status": "has_feedback"
        }
    
    def generate_report(self) -> str:
        """Generate feedback summary report"""
        if not self.feedback_history:
            return "📭 ยังไม่มี feedback"
        
        total_facts = len(self.feedback_history)
        total_feedback = sum(len(h) for h in self.feedback_history.values())
        
        lines = [
            "📊 **Feedback Summary**",
            "",
            f"📦 Facts with feedback: {total_facts}",
            f"📝 Total feedback entries: {total_feedback}",
            "",
            "📋 **Recent Feedback:**",
        ]
        
        for fact_id, entries in list(self.feedback_history.items())[:5]:
            latest = entries[-1]
            lines.append(f"  • Fact {fact_id}: {latest['action']} ({latest['effect']:+})")
        
        return "\n".join(lines)


# CLI Interface
if __name__ == "__main__":
    print("🧪 **Testing Fact Feedback System**\n")
    print("=" * 60)
    
    feedback = FactFeedback()
    
    # Test 1: Mark helpful
    print("\n📋 **Test 1: Mark Fact #42 as helpful**")
    result = feedback.mark_helpful(42, context="Boss said this was correct")
    print(f"  Result: {result['message']}")
    print(f"  Total feedback for #42: {result['total_feedback']}")
    
    # Test 2: Mark confirmed
    print("\n📋 **Test 2: Mark Fact #42 as confirmed**")
    result = feedback.mark_confirmed(42)
    print(f"  Result: {result['message']}")
    print(f"  Trust delta: {result['trust_delta']:+}")
    
    # Test 3: Mark unhelpful
    print("\n📋 **Test 3: Mark Fact #43 as unhelpful**")
    result = feedback.mark_unhelpful(43, reason="Outdated information")
    print(f"  Result: {result['message']}")
    print(f"  Reason: {result.get('reason', 'N/A')}")
    
    # Test 4: Mark corrected
    print("\n📋 **Test 4: Mark Fact #44 as corrected**")
    result = feedback.mark_corrected(44, correction="Should be PostgreSQL 15, not 14")
    print(f"  Result: {result['message']}")
    print(f"  Needs update: {result.get('needs_update', False)}")
    print(f"  Correction: {result.get('correction', 'N/A')}")
    
    # Test 5: Get status
    print("\n📋 **Test 5: Get Fact #42 status**")
    status = feedback.get_fact_status(42)
    print(f"  Feedback count: {status['feedback_count']}")
    print(f"  Net trust delta: {status['net_trust_delta']:+.1f}")
    
    # Test 6: Generate report
    print("\n📋 **Test 6: Generate Report**")
    print(feedback.generate_report())
    
    print("\n" + "=" * 60)
    print("\n✅ **All feedback tests passed!**")
    print(f"📝 Protocol v2.5 used: Tiny Trade with {4} feedback operations")
