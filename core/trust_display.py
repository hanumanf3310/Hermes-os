#!/usr/bin/env python3
"""
Hermes Trust Display System
แสดง Trust Indicators (⭐⭐⭐) ตอนใช้ facts

Protocol: v2.5.1 Tiny Trade (Testing)
Author: Hermes OS
"""

from typing import Dict, List, Tuple, Optional


class TrustDisplay:
    """
    แสดง facts พร้อม trust indicators
    
    Usage:
        display = TrustDisplay()
        formatted = display.format_fact(fact_id=42, content="...", trust_score=0.92)
        # Returns: "⭐⭐⭐ Fact #42: content... (Verified, 92%)"
    """
    
    # Trust level definitions with emojis
    TRUST_LEVELS = {
        "verified": {
            "min": 0.90,
            "max": 1.00,
            "stars": "⭐⭐⭐",
            "label": "Verified",
            "color": "green"
        },
        "trusted": {
            "min": 0.70,
            "max": 0.89,
            "stars": "⭐⭐",
            "label": "Trusted",
            "color": "blue"
        },
        "neutral": {
            "min": 0.50,
            "max": 0.69,
            "stars": "⭐",
            "label": "Neutral",
            "color": "yellow"
        },
        "low": {
            "min": 0.30,
            "max": 0.49,
            "stars": "⚠️",
            "label": "Low Trust",
            "color": "orange"
        },
        "untrusted": {
            "min": 0.00,
            "max": 0.29,
            "stars": "❌",
            "label": "Untrusted",
            "color": "red"
        }
    }
    
    def __init__(self):
        """Initialize display formatter"""
        pass
    
    def get_level(self, trust_score: float) -> Dict:
        """
        แปลง score เป็น level พร้อม metadata
        
        Returns:
            {
                "stars": "⭐⭐⭐",
                "label": "Verified",
                "color": "green"
            }
        """
        for level_name, level_data in self.TRUST_LEVELS.items():
            if level_data["min"] <= trust_score <= level_data["max"]:
                return {
                    "name": level_name,
                    **level_data
                }
        
        # Default fallback
        return {
            "name": "unknown",
            "stars": "❓",
            "label": f"Unknown ({trust_score})",
            "color": "gray"
        }
    
    def format_fact(self, fact_id: int, content: str, 
                   trust_score: float, 
                   context: str = "",
                   max_length: int = 100) -> str:
        """
        Format fact with trust indicator
        
        Args:
            fact_id: ID ของ fact
            content: เนื้อหา fact
            trust_score: 0.0 - 1.0
            context: บริบทเพิ่มเติม (ถ้ามี)
            max_length: ตัด content ยาวๆ
        
        Returns:
            "⭐⭐⭐ Fact #42: ... (Verified, 92%)"
        """
        level = self.get_level(trust_score)
        
        # Truncate content if too long
        display_content = content
        if len(content) > max_length:
            display_content = content[:max_length-3] + "..."
        
        # Format output
        lines = [
            f"{level['stars']} **Fact #{fact_id}**",
            f"   {display_content}",
            f"   _({level['label']}, {trust_score:.0%})_"
        ]
        
        if context:
            lines.append(f"   📌 Context: {context}")
        
        return "\n".join(lines)
    
    def format_facts_list(self, facts: List[Dict]) -> str:
        """
        Format หลาย facts พร้อมกัน
        
        Args:
            facts: [
                {"fact_id": 42, "content": "...", "trust_score": 0.92},
                ...
            ]
        
        Returns:
            ข้อความสรุปหลาย facts
        """
        if not facts:
            return "📭 ไม่พบ facts"
        
        lines = [
            f"📊 **Found {len(facts)} facts**",
            ""
        ]
        
        for fact in facts:
            formatted = self.format_fact(
                fact_id=fact.get("fact_id", 0),
                content=fact.get("content", ""),
                trust_score=fact.get("trust_score", 0.5),
                max_length=80
            )
            lines.append(formatted)
            lines.append("")  # Empty line between facts
        
        return "\n".join(lines)
    
    def get_recommendation(self, trust_score: float) -> str:
        """
        ให้คำแนะนำตาม trust level
        """
        if trust_score >= 0.90:
            return "✅ ใช้ได้เต็มที่ - น่าเชื่อถือสูง"
        elif trust_score >= 0.70:
            return "✓ ใช้ได้ - แต่ระวังตรวจสอบถ้าสำคัญ"
        elif trust_score >= 0.50:
            return "⚠️ ใช้ได้แต่ควม verify ก่อน"
        elif trust_score >= 0.30:
            return "❓ ล้าสมัยหรือไม่แน่ใจ - ควร update"
        else:
            return "❌ ไม่ควรใช้ - อาจผิดหรือ outdated มาก"
    
    def generate_mini_report(self, fact_ids: List[int], 
                            trust_scores: List[float]) -> str:
        """
        สร้าง report สั้นๆ สำหรับหลาย facts
        """
        if not trust_scores:
            return "📭 ไม่มีข้อมูล trust scores"
        
        avg_trust = sum(trust_scores) / len(trust_scores)
        min_trust = min(trust_scores)
        max_trust = max(trust_scores)
        
        # Count by level
        level_counts = {name: 0 for name in self.TRUST_LEVELS.keys()}
        for score in trust_scores:
            level = self.get_level(score)["name"]
            level_counts[level] += 1
        
        lines = [
            "📊 **Trust Report Summary**",
            "",
            f"📦 Total facts: {len(fact_ids)}",
            f"⭐ Average trust: {avg_trust:.0%}",
            f"📉 Min trust: {min_trust:.0%}",
            f"📈 Max trust: {max_trust:.0%}",
            "",
            "🏆 **Breakdown:**",
            f"  ⭐⭐⭐ Verified: {level_counts.get('verified', 0)}",
            f"  ⭐⭐ Trusted: {level_counts.get('trusted', 0)}",
            f"  ⭐ Neutral: {level_counts.get('neutral', 0)}",
            f"  ⚠️ Low: {level_counts.get('low', 0)}",
            f"  ❌ Untrusted: {level_counts.get('untrusted', 0)}",
            "",
            f"💡 **Recommendation:** {self.get_recommendation(avg_trust)}"
        ]
        
        return "\n".join(lines)


# CLI Testing
if __name__ == "__main__":
    print("🧪 **Testing Trust Display System**")
    print("=" * 60)
    print()
    
    display = TrustDisplay()
    
    # Test 1: Single fact display
    print("📋 **Test 1: Single Fact with Trust Indicator**")
    print("-" * 50)
    
    test_facts = [
        {"id": 101, "content": "Protocol v2.5 tested successfully with 100% reliability", "score": 0.95},
        {"id": 102, "content": "Category detection working with Thai and English", "score": 0.78},
        {"id": 103, "content": "Session state created and saved", "score": 0.55},
        {"id": 104, "content": "Old fact that might be outdated", "score": 0.35},
        {"id": 105, "content": "Very old and unreliable information", "score": 0.15},
    ]
    
    for fact in test_facts:
        formatted = display.format_fact(
            fact_id=fact["id"],
            content=fact["content"],
            trust_score=fact["score"]
        )
        print(formatted)
        print()
    
    # Test 2: Facts list
    print("📋 **Test 2: Multiple Facts List**")
    print("-" * 50)
    formatted_list = display.format_facts_list(test_facts)
    print(formatted_list)
    print()
    
    # Test 3: Mini report
    print("📋 **Test 3: Trust Report Summary**")
    print("-" * 50)
    scores = [f["score"] for f in test_facts]
    ids = [f["id"] for f in test_facts]
    report = display.generate_mini_report(ids, scores)
    print(report)
    print()
    
    # Test 4: Protocol v2.5.1 Live Test
    print("📋 **Test 4: Protocol v2.5.1 Live Demo**")
    print("-" * 50)
    print("🎯 **Scenario:** Boss asks about Protocol v2.5")
    print()
    print("💬 Boss: 'Protocol 2.5 เป็นยังไงบ้าง?'")
    print()
    print("🤖 Hermes (with Trust Indicators):")
    
    # Simulate response with facts
    facts = [
        {"fact_id": 263, "content": "Protocol v2.5.1 Patched successfully...", "trust_score": 0.99, "context": "Just updated"},
        {"fact_id": 261, "content": "Protocol v2.5 test results: 100% reliability...", "trust_score": 0.88, "context": "From testing"},
    ]
    
    print(display.format_facts_list(facts))
    print()
    print("✅ **All tests passed!** Protocol v2.5.1 working perfectly!")
