"""
Hermes Category Auto-Detection Module
ตรวจจับ category อัตโนมัติจาก content

Supports: Thai + English
Categories: user, project, tech, security, environment

Author: Hermes OS
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """ผลลัพธ์การตรวจจับ category"""
    category: Optional[str]
    confidence: float
    matched_patterns: List[str]
    requires_confirmation: bool = False
    reason: str = ""


class CategoryDetector:
    """ตรวจจับ category อัตโนมัติจาก content"""
    
    # Category definitions with patterns and keywords (Thai + English)
    CATEGORY_RULES = {
        "user": {
            "patterns_th": [
                r"(?:ฉัน|ผม|ข้าพเจ้า)ชอบ.*",
                r"(?:ฉัน|ผม|ข้าพเจ้า)ไม่ชอบ.*",
                r"(?:ฉัน|ผม|ข้าพเจ้า)ต้องการ.*",
                r"(?:ฉัน|ผม|ข้าพเจ้า)อยากได้.*",
                r"(?:ฉัน|ผม|ข้าพเจ้า)ชอบให้.*",
            ],
            "patterns_en": [
                r"I prefer.*",
                r"I like.*",
                r"I don't like.*",
                r"I need.*",
                r"I want.*",
                r"Boss prefers.*",
                r"Boss likes.*",
            ],
            "keywords_th": ["ชอบ", "ไม่ชอบ", "อยาก", "ต้องการ", "prefer", "ชอบให้"],
            "keywords_en": ["prefer", "like", "want", "need"],
            "confidence_boost": 0.2,
            "requires_confirmation": False,
            "sensitive": False,
        },
        
        "project": {
            "patterns_th": [
                r"โปรเจกต์นี้.*",
                r"project นี้.*",
                r"โปรเจคนี้.*",
                r" repo นี้.*",
                r" repository นี้.*",
            ],
            "patterns_en": [
                r"This project.*",
                r"The project.*",
                r"Our project.*",
                r"We use.*",
                r"The stack.*",
                r"Tech stack.*",
                r"Architecture.*",
            ],
            "keywords_th": ["โปรเจกต์", "โปรเจค", "project", "repo", "repository", "ใช้"],
            "keywords_en": ["project", "repo", "repository", "stack", "architecture"],
            "confidence_boost": 0.15,
            "requires_confirmation": False,
            "sensitive": False,
        },
        
        "tech": {
            "patterns_th": [
                r"API.*",
                r"ฟังก์ชัน.*",
                r"database.*",
                r"ใช้.*Python",
                r"ใช้.*React",
                r"ใช้.*Node",
                r"ระบบ.*",
            ],
            "patterns_en": [
                r"^API.*",
                r"^Function.*",
                r"^Database.*",
                r"^Endpoint.*",
                r"^Service.*",
                r"Uses?\s+(?:python|react|node|go|rust)",
                r"Code.*",
                r"Implementation.*",
            ],
            "keywords_th": ["API", "ฟังก์ชัน", "database", "docker", "kubernetes", "โค้ด", "code", "ระบบ"],
            "keywords_en": ["API", "function", "database", "docker", "kubernetes", "code", "implementation", "endpoint"],
            "confidence_boost": 0.1,
            "requires_confirmation": False,
            "sensitive": False,
        },
        
        "security": {
            "patterns_th": [
                r"password.*",
                r"token.*",
                r"secret.*",
                r"key.*",
                r"รหัสผ่าน.*",
            ],
            "patterns_en": [
                r"^Password.*",
                r"^Token.*",
                r"^Secret.*",
                r"^Credential.*",
                r"^API Key.*",
                r"^Private key.*",
                r"Auth.*",
            ],
            "keywords_th": ["password", "token", "secret", "key", "รหัสผ่าน", "ความลับ"],
            "keywords_en": ["password", "token", "secret", "key", "credential", "auth"],
            "confidence_boost": 0.0,
            "requires_confirmation": True,  # ต้องยืนยันก่อนบันทึก
            "sensitive": True,
        },
        
        "environment": {
            "patterns_th": [
                r"ทำงานอยู่.*",
                r"环境.*",
                r"ใช้งาน.*WSL",
                r"ใช้งาน.*Windows",
            ],
            "patterns_en": [
                r"^Using\s+WSL",
                r"^Working on\s+(?:Windows|Mac|Linux)",
                r"^Environment.*",
                r"^OS.*",
                r"^Platform.*",
            ],
            "keywords_th": ["WSL", "Windows", "Mac", "Linux", "Ubuntu", "environment", "ระบบปฏิบัติการ"],
            "keywords_en": ["WSL", "Windows", "Mac", "Linux", "Ubuntu", "environment", "OS", "platform"],
            "confidence_boost": 0.15,
            "requires_confirmation": False,
            "sensitive": False,
            "auto_detect_from_system": True,  # สามารถ detect จาก system info ได้
        },
    }
    
    def __init__(self):
        """Initialize detector"""
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, Dict]:
        """Compile regex patterns for performance"""
        compiled = {}
        for category, rules in self.CATEGORY_RULES.items():
            compiled[category] = {
                "patterns_th": [re.compile(p, re.IGNORECASE) for p in rules["patterns_th"]],
                "patterns_en": [re.compile(p, re.IGNORECASE) for p in rules["patterns_en"]],
                **{k: v for k, v in rules.items() if k not in ["patterns_th", "patterns_en"]}
            }
        return compiled
    
    def detect(self, content: str, context: Optional[Dict] = None) -> DetectionResult:
        """
        ตรวจจับ category จาก content
        
        Args:
            content: ข้อความที่จะวิเคราะห์
            context: Context เพิ่มเติม (optional)
        
        Returns:
            DetectionResult ที่มี category, confidence, และ matched patterns
        """
        if not content or len(content.strip()) < 5:
            return DetectionResult(
                category=None,
                confidence=0.0,
                matched_patterns=[],
                reason="Content too short"
            )
        
        scores = {}
        matched_patterns = {}
        
        for category, rules in self.compiled_patterns.items():
            score = 0.4  # Base score
            patterns_matched = []
            
            # Pattern matching (Thai + English)
            for i, pattern in enumerate(rules["patterns_th"]):
                if pattern.search(content):
                    score += 0.35
                    original = self.CATEGORY_RULES[category]["patterns_th"][i]
                    patterns_matched.append(f"th:{original}")
                    break  # Only count once per category
            
            for i, pattern in enumerate(rules["patterns_en"]):
                if pattern.search(content):
                    score += 0.35
                    original = self.CATEGORY_RULES[category]["patterns_en"][i]
                    patterns_matched.append(f"en:{original}")
                    break
            
            # Keyword matching
            keywords_th = rules.get("keywords_th", [])
            keywords_en = rules.get("keywords_en", [])
            
            content_lower = content.lower()
            keyword_matches = sum(1 for kw in keywords_th + keywords_en if kw.lower() in content_lower)
            score += min(0.25, keyword_matches * 0.08)
            
            # Confidence boost
            score += rules.get("confidence_boost", 0)
            
            # Cap at 1.0
            score = min(1.0, max(0, score))
            
            scores[category] = score
            matched_patterns[category] = patterns_matched
        
        # Find best match
        if scores:
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]
            
            # Determine if confirmation needed
            requires_confirmation = self.CATEGORY_RULES[best_category].get("requires_confirmation", False)
            
            if best_score < 0.5:
                return DetectionResult(
                    category=None,
                    confidence=best_score,
                    matched_patterns=matched_patterns[best_category],
                    requires_confirmation=True,
                    reason=f"Low confidence ({best_score:.2f}) for category '{best_category}'"
                )
            
            return DetectionResult(
                category=best_category,
                confidence=best_score,
                matched_patterns=matched_patterns[best_category],
                requires_confirmation=requires_confirmation,
                reason=f"Matched patterns: {matched_patterns[best_category]}"
            )
        
        return DetectionResult(
            category=None,
            confidence=0.0,
            matched_patterns=[],
            requires_confirmation=True,
            reason="No category detected"
        )
    
    def detect_with_fallback(self, content: str, preferred_category: Optional[str] = None) -> DetectionResult:
        """
        ตรวจจับพร้อม fallback category
        
        Args:
            content: ข้อความที่จะวิเคราะห์
            preferred_category: Category ที่ user บอกไว้ (if any)
        
        Returns:
            DetectionResult
        """
        if preferred_category:
            # Validate preferred category
            if preferred_category in self.CATEGORY_RULES:
                return DetectionResult(
                    category=preferred_category,
                    confidence=1.0,
                    matched_patterns=["user_specified"],
                    requires_confirmation=False,
                    reason="User specified"
                )
        
        return self.detect(content)
    
    def get_category_description(self, category: str) -> str:
        """คืนคำอธิบาย category"""
        descriptions = {
            "user": "ค่าที่ผู้ใช้ตั้งค่า/ความชอบ",
            "project": "ข้อมูลเกี่ยวกับโปรเจกต์",
            "tech": "เทคนิค/เทคโนโลยี/โค้ด",
            "security": "ความปลอดภัย/credentials (ระวัง!)",
            "environment": "สภาพแวดล้อม/OA/เครื่อง",
        }
        return descriptions.get(category, "ไม่ระบุ")
    
    def format_detection_result(self, result: DetectionResult) -> str:
        """แสดงผลลัพธ์ในรูปแบบที่อ่านง่าย"""
        if result.category:
            desc = self.get_category_description(result.category)
            lines = [
                f"🎯 Category: {result.category} ({desc})",
                f"📊 Confidence: {result.confidence:.0%}",
            ]
            
            if result.requires_confirmation:
                lines.append("⚠️ Requires confirmation before saving")
            
            if result.matched_patterns:
                lines.append(f"🔍 Matched: {', '.join(result.matched_patterns[:2])}")
            
            return "\n".join(lines)
        else:
            return f"❓ No category detected (confidence: {result.confidence:.0%})\n   Reason: {result.reason}"


# Static detector instance for reuse
_detector = None

def get_detector():
    """Get global detector instance (singleton)"""
    global _detector
    if _detector is None:
        _detector = CategoryDetector()
    return _detector


def auto_detect_category(content: str, preferred: Optional[str] = None) -> DetectionResult:
    """
    Convenience function สำหรับ detect category
    
    Example:
        result = auto_detect_category("ฉันชอบใช้ VS Code")
        # result.category == "user"
        # result.confidence == 0.9+
    """
    detector = get_detector()
    return detector.detect_with_fallback(content, preferred)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    detector = CategoryDetector()
    
    if len(sys.argv) < 2:
        # Test mode - run through sample texts
        test_cases = [
            ("ฉันชอบให้สรุปสั้นๆ", None),
            ("โปรเจกต์นี้ใช้ PostgreSQL", None),
            ("API นี้ต้องมี rate limiting", None),
            ("ทำงานอยู่ WSL บน Windows", None),
            ("This is the password: secret123", None),
            ("I prefer dark mode", None),
            ("The project uses React and Node.js", None),
            ("some random text", "project"),  # With fallback
        ]
        
        print("🧪 Testing Category Auto-Detection\n")
        print("=" * 60)
        
        for text, preferred in test_cases:
            result = detector.detect_with_fallback(text, preferred)
            print(f"\n📝 Input: \"{text}\"")
            if preferred:
                print(f"   Preferred: {preferred}")
            print(detector.format_detection_result(result))
            print("-" * 60)
    else:
        # Command line mode
        text = " ".join(sys.argv[1:])
        result = detector.detect(text)
        print(f"Input: {text}")
        print(detector.format_detection_result(result))