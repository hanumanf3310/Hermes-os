"""
Hermes OS Phase 3 - Pre-flight Analyzer Module
Analyzes task complexity and provides routing recommendations.
"""

import re
import json
from typing import Dict, Any


class TaskAnalyzer:
    """
    Analyzes task messages to determine complexity and routing recommendation.

    Scoring system (0-10 points):
    - 0-3: Simple → Direct routing
    - 4-7: Medium → Direct (with suggestion to consider fleet)
    - 8-10: Complex → Fleet routing
    """

    # Scoring weights
    WEIGHTS = {
        "length": 2,
        "technical_terms": 2,
        "multi_file": 2,
        "research": 2,
        "dependencies": 2
    }

    # Technical terms (English and Thai)
    TECHNICAL_TERMS = [
        # Programming/Development
        "code", "program", "script", "function", "class", "method", "variable",
        "debug", "compile", "build", "deploy", "git", "repository", "commit",
        "โปรแกรม", "โค้ด", "ฟังก์ชัน", "คลาส", "เมธอด", "ตัวแปร", "ดีบั๊ก",
        "เขียน", "พัฒนา", "develop", "development",

        # APIs and Services
        "api", "rest", "graphql", "endpoint", "webhook", "service",
        "microservice", "server", "backend", "frontend", "fullstack",
        "เซิร์ฟเวอร์", "แบ็กเอนด์", "ฟรอนต์เอนด์", "เอพีไอ",

        # Databases
        "database", "db", "sql", "nosql", "query", "schema", "migration",
        "table", "collection", "index", "ฐานข้อมูล", "ดาต้าเบส",

        # Frameworks/Languages
        "python", "javascript", "js", "typescript", "ts", "react", "vue",
        "angular", "django", "flask", "fastapi", "node", "nodejs", "express",
        "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "cloud",
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
        "jwt", "stripe", "sendgrid", "csv",
        "ไพธอน", "จาวาสคริปต์", "รีแอค", "ด็อกเกอร์",

        # File/Project operations
        "refactor", "refactoring", "รีแฟคเตอร์", "มิเกรท", "migration",
    ]

    # Multi-file indicators
    MULTI_FILE_INDICATORS = [
        "project", "projects", "โปรเจค", "โปรเจกต์", "โครงการ",
        "multiple files", "many files", "several files", "all files",
        "ทุกไฟล์", "หลายไฟล์", "ไฟล์ทั้งหมด",
        "refactor", "refactoring", "รีแฟคเตอร์", "ปรับปรุงโครงสร้าง",
        "module", "modules", "package", "packages",
        "โมดูล", "แพ็กเกจ", "ส่วนประกอบ",
        "web app", "webapp", "app", "application",
        "system", "architecture", "microservice", "microservices",
        "full stack", "fullstack", "ครบวงจร",
    ]

    # File extensions
    FILE_EXTENSIONS = [
        r'\.py', r'\.js', r'\.ts', r'\.jsx', r'\.tsx', r'\.json',
        r'\.yaml', r'\.yml', r'\.md', r'\.txt', r'\.csv', r'\.xml',
        r'\.html', r'\.css', r'\.scss', r'\.sass', r'\.php', r'\.rb',
        r'\.go', r'\.rs', r'\.java', r'\.c', r'\.cpp', r'\.h',
    ]

    # Research indicators
    RESEARCH_INDICATORS = [
        "research", "compare", "evaluate", "find out", "investigate",
        "learn about", "look up", "search for", "analyze", "study",
        "วิจัย", "เปรียบเทียบ", "ประเมิน", "หาข้อมูล", "สำรวจ", "เรียนรู้",
        "ค้นหา", "วิเคราะห์", "ศึกษา", "รีวิว", "review",
        "best way", "best", "ดีที่สุด", "วิธีที่ดีที่สุด",
    ]

    # Question words (for research detection)
    QUESTION_WORDS = [
        "what", "how", "why", "which", "when", "where", "who",
        "what's", "how's", "why's",
        "อะไร", "อย่างไร", "ยังไง", "ทำไม", "อันไหน", "เมื่อไหร่", "ที่ไหน",
        "ใคร", "กี่", "กันแน่", "หรือไม่", "ได้ยังไง",
    ]

    # Dependency indicators
    DEPENDENCY_INDICATORS = [
        "depends on", "requires", "need to", "integrate with", "connect to",
        "uses", "using", "based on", "built on", "relies on",
        "depends", "required", "necessary", "prerequisite",
        "ขึ้นอยู่กับ", "ต้องการ", "จำเป็นต้อง", "เชื่อมต่อ", "เชื่อมโยง",
        "ใช้ร่วมกับ", "ทำงานร่วมกับ", "อินทิเกรต", "ใช้งาน",
        "ติดตั้ง", "install", "dependency", "dependencies", "ไลบรารี่",
    ]

    EXTERNAL_SERVICE_TERMS = [
        "api", "database", "db", "server", "webhook", "service",
        "third party", "third-party", "external", "payment", "connection",
    ]

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the analyzer with optional configuration.

        Args:
            config: Dictionary with custom thresholds and weights
        """
        self.config = config or {}
        self.weights = self.config.get("weights", self.WEIGHTS)

        # Compile regex patterns for better performance
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.patterns = {
            "tech_terms": re.compile(
                r'\b(' + '|'.join(re.escape(term) for term in self.TECHNICAL_TERMS) + r')\b',
                re.IGNORECASE
            ),
            "multi_file": re.compile(
                r'\b(' + '|'.join(re.escape(indicator) for indicator in self.MULTI_FILE_INDICATORS) + r')\b',
                re.IGNORECASE
            ),
            "file_ext": re.compile(
                '(' + '|'.join(self.FILE_EXTENSIONS) + r')\b',
                re.IGNORECASE
            ),
            "research": re.compile(
                r'\b(' + '|'.join(re.escape(indicator) for indicator in self.RESEARCH_INDICATORS) + r')\b',
                re.IGNORECASE
            ),
            "question_word": re.compile(
                r'^(' + '|'.join(re.escape(word) for word in self.QUESTION_WORDS) + r')\b',
                re.IGNORECASE
            ),
            "dependency": re.compile(
                r'\b(' + '|'.join(re.escape(indicator) for indicator in self.DEPENDENCY_INDICATORS) + r')\b',
                re.IGNORECASE
            ),
        }

    def _count_unique_terms(self, message: str, terms: list) -> int:
        """Count unique indicator terms using fast substring matching."""
        lower_message = message.lower()
        matched = set()
        for term in terms:
            term_l = term.lower()
            if term_l in lower_message:
                matched.add(term_l)
        return len(matched)

    def _has_question_word_start(self, message: str) -> bool:
        """Check whether message starts with an English or Thai question word."""
        text = message.lstrip().lower()
        if not text:
            return False

        for word in ("what", "how", "why", "which", "when", "where", "who"):
            if text.startswith(word) and (len(text) == len(word) or not text[len(word)].isalpha()):
                return True
        for word in ("what's", "how's", "why's"):
            if text.startswith(word):
                return True
        for word in ("อะไร", "อย่างไร", "ยังไง", "ทำไม", "อันไหน", "เมื่อไหร่", "ที่ไหน", "ใคร", "กี่", "กันแน่", "หรือไม่", "ได้ยังไง"):
            if text.startswith(word):
                return True
        return False

    def _calculate_length_score(self, message: str) -> int:
        """
        Calculate score based on message length.

        - < 15 chars: 0
        - 15-29 chars: 1
        - 30-59 chars: 2
        - >= 60 chars: 3
        """
        length = len(message.strip())
        if length < 15:
            return 0
        elif length < 30:
            return 1
        elif length < 60:
            return 2
        else:
            return 3

    def _calculate_tech_terms_score(self, message: str) -> int:
        """
        Calculate score based on technical terms.

        - 0 terms: 0
        - 1-2 terms: 1
        - 3+ terms: 2
        """
        unique_terms = self._count_unique_terms(message, self.TECHNICAL_TERMS)

        if unique_terms == 0:
            return 0
        elif unique_terms <= 2:
            return 1
        elif unique_terms <= 4:
            return 2
        else:
            return 3

    def _calculate_multi_file_score(self, message: str) -> int:
        """
        Calculate score based on multi-file indicators.

        - Keywords: project, multiple files, several files, all files, refactor
        - File extensions mentioned
        """
        unique_indicators = self._count_unique_terms(message, self.MULTI_FILE_INDICATORS)
        file_ext_matches = self.patterns["file_ext"].findall(message)
        unique_exts = len(set(ext.lower() for ext in file_ext_matches))
        lower_message = message.lower()
        tech_terms = self._count_unique_terms(message, self.TECHNICAL_TERMS)

        if unique_exts >= 2 or unique_indicators >= 3:
            return 3
        if unique_indicators >= 1 or unique_exts == 1:
            if tech_terms >= 4 or any(token in lower_message for token in ("microservice", "microservices", "architecture", "full stack", "fullstack", "all files", "many files", "several files", "multiple files")):
                return 2
            return 1
        if tech_terms >= 5 and any(token in lower_message for token in ("web app", "app", "system", "architecture", "project", "โปรเจค", "โปรเจกต์", "โครงการ")):
            return 3
        return 0

    def _calculate_research_score(self, message: str) -> int:
        """
        Calculate score based on research indicators.

        - Keywords: research, compare, evaluate, find out, investigate
        - Question words at start
        """
        research_matches = self._count_unique_terms(message, self.RESEARCH_INDICATORS)
        question_start = self._has_question_word_start(message)
        has_question_mark = "?" in message

        if research_matches >= 2:
            return 2
        if research_matches == 1:
            return 1
        if question_start:
            return 1
        if has_question_mark and self._count_unique_terms(message, ["best", "ดีที่สุด", "วิธีที่ดีที่สุด", "compare", "เปรียบเทียบ"]) > 0:
            return 2
        return 0

    def _calculate_dependencies_score(self, message: str) -> int:
        """
        Calculate score based on dependency indicators.

        - Keywords: depends on, require, need to, integrate with, connect to
        - References to external services
        """
        dependency_matches = self._count_unique_terms(message, self.DEPENDENCY_INDICATORS)
        external_services = self._count_unique_terms(message, self.EXTERNAL_SERVICE_TERMS)

        if dependency_matches > 0 and external_services > 0:
            return 2
        if dependency_matches > 1 or external_services > 1:
            return 2
        if dependency_matches > 0 or external_services > 0:
            return 1
        return 0

    def _calculate_confidence(self, factors: Dict[str, int]) -> float:
        """
        Calculate confidence score based on factor distribution.

        More factors with non-zero values = higher confidence
        """
        non_zero_factors = sum(1 for score in factors.values() if score > 0)
        total_factors = len(factors)

        # Base confidence on how many factors contributed
        confidence = 0.5 + (non_zero_factors / total_factors) * 0.5

        # Adjust based on total score - extreme scores have higher confidence
        total_score = sum(factors.values())
        if total_score == 0 or total_score >= 8:
            confidence = min(1.0, confidence + 0.1)

        return round(confidence, 2)

    def _get_recommendation(self, score: int) -> str:
        """
        Get routing recommendation based on total score.

        - 0-3: direct
        - 4-7: direct (with note)
        - 8-10: fleet
        """
        if score <= 3:
            return "direct"
        elif score <= 6:
            return "direct"  # Fleet suggested for scores > 5
        else:
            return "fleet"

    def _get_suggestion(self, score: int) -> str:
        """Get suggestion message based on score."""
        if score <= 3:
            return "This is a simple task, suitable for direct handling."
        elif score <= 5:
            return "Medium complexity task. Can be handled directly or with simple decomposition."
        elif score <= 7:
            return "Consider using fleet for better parallelization and efficiency."
        else:
            return "Complex task requiring multiple subtasks. Fleet execution recommended."

    def analyze(self, message: str) -> Dict[str, Any]:
        """
        Analyze task complexity.

        Args:
            message: The task message to analyze

        Returns:
            Dictionary containing:
            - score: int (0-10)
            - factors: dict of individual scores
            - recommendation: str ("direct" | "fleet")
            - confidence: float (0.0 - 1.0)
            - suggestion: str
        """
        if not message or not message.strip():
            return {
                "score": 0,
                "factors": {name: 0 for name in list(self.weights.keys()) + ["question_word"]},
                "recommendation": "direct",
                "confidence": 0.0,
                "suggestion": "Empty message provided."
            }

        question_word = 1 if self._has_question_word_start(message) else 0

        # Calculate individual factor scores
        factors = {
            "length": self._calculate_length_score(message),
            "technical_terms": self._calculate_tech_terms_score(message),
            "multi_file": self._calculate_multi_file_score(message),
            "research": self._calculate_research_score(message),
            "dependencies": self._calculate_dependencies_score(message),
            "question_word": question_word,
        }

        # Calculate total score
        total_score = min(10, sum(factors.values()))

        # Get recommendation and confidence
        recommendation = self._get_recommendation(total_score)
        confidence = self._calculate_confidence(factors)
        suggestion = self._get_suggestion(total_score)

        return {
            "score": total_score,
            "factors": factors,
            "recommendation": recommendation,
            "confidence": confidence,
            "suggestion": suggestion
        }

    def get_factors(self) -> Dict[str, Any]:
        """
        Return scoring criteria and configuration.

        Returns:
            Dictionary with scoring rules and weights
        """
        return {
            "weights": self.weights,
            "criteria": {
                "length": {
                    "description": "Message length complexity",
                    "score_0": "< 50 characters",
                    "score_1": "50-200 characters",
                    "score_2": "> 200 characters",
                    "max_score": 2
                },
                "technical_terms": {
                    "description": "Presence of technical terms",
                    "score_0": "0 terms",
                    "score_1": "1-2 terms",
                    "score_2": "3+ terms",
                    "max_score": 2,
                    "terms": self.TECHNICAL_TERMS[:20]  # Sample
                },
                "multi_file": {
                    "description": "Indicates multi-file work",
                    "score_0": "No indicators",
                    "score_1": "1 file extension mentioned",
                    "score_2": "Multiple files or refactoring",
                    "max_score": 2,
                    "indicators": self.MULTI_FILE_INDICATORS[:10]  # Sample
                },
                "research": {
                    "description": "Requires research",
                    "score_0": "No research indicators",
                    "score_2": "Research keywords or question words",
                    "max_score": 2,
                    "indicators": self.RESEARCH_INDICATORS[:10]  # Sample
                },
                "dependencies": {
                    "description": "Has dependencies",
                    "score_0": "No dependencies",
                    "score_2": "Dependencies or external services",
                    "max_score": 2,
                    "indicators": self.DEPENDENCY_INDICATORS[:10]  # Sample
                }
            },
            "routing_rules": {
                "0-3": "direct - Simple task",
                "4-7": "direct - Medium task (consider fleet)",
                "8-10": "fleet - Complex task"
            }
        }

    def batch_analyze(self, messages: list) -> list:
        """
        Analyze multiple messages at once.

        Args:
            messages: List of message strings

        Returns:
            List of analysis results
        """
        return [self.analyze(msg) for msg in messages]


# Convenience function for direct usage
def analyze_task(message: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Quick analysis function.

    Args:
        message: Task message to analyze
        config: Optional configuration

    Returns:
        Analysis result dictionary
    """
    analyzer = TaskAnalyzer(config)
    return analyzer.analyze(message)


if __name__ == "__main__":
    # Demo usage
    analyzer = TaskAnalyzer()

    test_messages = [
        "สวัสดี",
        "บอกวันที่วันนี้หน่อย",
        "เขียน Python script เปลี่ยนชื่อไฟล์",
        "สร้าง web app ร้านค้าใช้ React + Node.js + Database",
        "Research API ที่ดีที่สุดสำหรับ payment",
    ]

    print("=" * 80)
    print("HERMES OS PHASE 3 - PRE-FLIGHT ANALYZER")
    print("=" * 80)

    for msg in test_messages:
        result = analyzer.analyze(msg)
        print(f"\nMessage: {msg}")
        print(f"  Score: {result['score']}/10")
        print(f"  Factors: {result['factors']}")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Suggestion: {result['suggestion']}")

    print("\n" + "=" * 80)
    print("Scoring Criteria:")
    criteria = analyzer.get_factors()
    print(json.dumps(criteria, indent=2, ensure_ascii=False))
