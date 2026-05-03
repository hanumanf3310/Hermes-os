"""
Unit Tests for Hermes OS Phase 3 - Pre-flight Analyzer
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import TaskAnalyzer, analyze_task


class TestTaskAnalyzer(unittest.TestCase):
    """Test cases for TaskAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = TaskAnalyzer()

    # Test 1: Simple greeting (Score 0-2)
    def test_simple_greeting_thai(self):
        """Test simple Thai greeting."""
        result = self.analyzer.analyze("สวัสดี")
        self.assertLessEqual(result["score"], 2)
        self.assertEqual(result["recommendation"], "direct")
        self.assertGreaterEqual(result["confidence"], 0.5)

    # Test 2: Simple English greeting
    def test_simple_greeting_english(self):
        """Test simple English greeting."""
        result = self.analyzer.analyze("Hello")
        self.assertLessEqual(result["score"], 2)
        self.assertEqual(result["recommendation"], "direct")

    # Test 3: Simple question (Score 1-3)
    def test_simple_question(self):
        """Test asking for current date."""
        result = self.analyzer.analyze("บอกวันที่วันนี้หน่อย")
        self.assertLessEqual(result["score"], 3)
        self.assertEqual(result["recommendation"], "direct")
        self.assertGreaterEqual(result["factors"]["length"], 1)

    # Test 4: Technical task with single file (Score 5-7)
    def test_single_file_tech_task(self):
        """Test Python script writing task."""
        result = self.analyzer.analyze("เขียน Python script เปลี่ยนชื่อไฟล์")
        self.assertGreaterEqual(result["score"], 4)
        self.assertLessEqual(result["score"], 7)
        self.assertGreaterEqual(result["factors"]["technical_terms"], 1)
        self.assertEqual(result["factors"]["multi_file"], 0)  # Single file

    # Test 5: Empty message
    def test_empty_message(self):
        """Test empty message handling."""
        result = self.analyzer.analyze("")
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["recommendation"], "direct")
        self.assertEqual(result["confidence"], 0.0)

    # Test 6: Complex multi-component project (Score 8-10)
    def test_complex_project(self):
        """Test complex e-commerce project."""
        result = self.analyzer.analyze(
            "สร้าง web app ร้านค้าใช้ React + Node.js + Database"
        )
        self.assertGreaterEqual(result["score"], 7)
        self.assertEqual(result["recommendation"], "fleet")
        self.assertGreaterEqual(result["factors"]["technical_terms"], 2)
        self.assertGreaterEqual(result["factors"]["dependencies"], 1)

    # Test 7: Research task
    def test_research_task(self):
        """Test research API task."""
        result = self.analyzer.analyze("Research API ที่ดีที่สุดสำหรับ payment")
        self.assertGreaterEqual(result["score"], 6)
        self.assertGreaterEqual(result["factors"]["research"], 1)

    # Test 8: Multi-file refactoring task
    def test_multi_file_refactor(self):
        """Test refactoring across multiple files."""
        result = self.analyzer.analyze("Refactor และปรับปรุงโครงสร้างทุกไฟล์ในโปรเจค")
        self.assertGreaterEqual(result["score"], 6)
        self.assertGreaterEqual(result["factors"]["multi_file"], 1)

    # Test 9: Task with dependencies
    def test_task_with_dependencies(self):
        """Test task mentioning external dependencies."""
        result = self.analyzer.analyze(
            "สร้างระบบ that integrates with external API and requires database connection"
        )
        self.assertGreaterEqual(result["score"], 6)
        self.assertGreaterEqual(result["factors"]["dependencies"], 1)

    # Test 10: English question with research
    def test_english_question_research(self):
        """Test English question starting with question word."""
        result = self.analyzer.analyze("How do I deploy a Django app to AWS?")
        self.assertGreaterEqual(result["score"], 4)
        self.assertGreaterEqual(result["factors"]["research"], 1)
        self.assertGreaterEqual(result["factors"]["question_word"], 1)

    # Test 11: Question starting with Thai question word
    def test_thai_question_format(self):
        """Test Thai question format."""
        result = self.analyzer.analyze("อะไรคือวิธีที่ดีที่สุดในการเขียนโปรแกรม")
        self.assertGreaterEqual(result["factors"]["research"], 1)

    # Test 12: Long complex task
    def test_long_complex_task(self):
        """Test very long complex task."""
        message = (
            "สร้างระบบร้านค้าออนไลน์แบบครบวงจรโดยใช้ Python Django สำหรับ backend, "
            "React สำหรับ frontend, PostgreSQL สำหรับ database และต้องเชื่อมต่อกับ "
            "Stripe API สำหรับการชำระเงิน, SendGrid สำหรับส่งอีเมล, และต้องมีระบบ "
            "authentication ด้วย JWT tokens โดยแบ่งเป็น microservices architecture"
        )
        result = self.analyzer.analyze(message)
        self.assertEqual(result["score"], 10)
        self.assertEqual(result["recommendation"], "fleet")
        self.assertGreaterEqual(result["confidence"], 0.8)

    # Test 13: Medium complexity task
    def test_medium_complexity_task(self):
        """Test medium complexity task."""
        result = self.analyzer.analyze(
            "เขียนโปรแกรม Python ง่ายๆ สำหรับจัดการไฟล์ CSV"
        )
        self.assertGreaterEqual(result["score"], 4)
        self.assertLessEqual(result["score"], 7)

    # Test 14: File extension mentions
    def test_file_extension_detection(self):
        """Test detection of multiple file extensions."""
        result = self.analyzer.analyze("แก้ไขไฟล์ .py และ .js ในโปรเจค")
        self.assertGreaterEqual(result["factors"]["multi_file"], 1)

    # Test 15: Batch analyze
    def test_batch_analyze(self):
        """Test batch analysis function."""
        messages = ["Hello", "สวัสดี", "สร้าง web app"]
        results = self.analyzer.batch_analyze(messages)
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIn("score", result)
            self.assertIn("recommendation", result)

    # Test 16: Get factors
    def test_get_factors(self):
        """Test get_factors method."""
        factors = self.analyzer.get_factors()
        self.assertIn("weights", factors)
        self.assertIn("criteria", factors)
        self.assertIn("routing_rules", factors)
        self.assertEqual(factors["weights"]["length"], 2)

    # Test 17: Convenience function
    def test_convenience_function(self):
        """Test analyze_task convenience function."""
        result = analyze_task("Test message with Python code")
        self.assertIn("score", result)
        self.assertIn("recommendation", result)

    # Test 18: Custom configuration
    def test_custom_configuration(self):
        """Test analyzer with custom configuration."""
        custom_config = {"weights": {"length": 3, "technical_terms": 1}}
        analyzer = TaskAnalyzer(custom_config)
        factors = analyzer.get_factors()
        self.assertEqual(factors["weights"]["length"], 3)

    # Test 19: Confidence calculation
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # Very simple task should have lower confidence
        simple = self.analyzer.analyze("Hi")
        # Complex task should have higher confidence
        complex_msg = self.analyzer.analyze(
            "สร้างระบบเต็มรูปแบบด้วย React Node.js Database API"
        )
        self.assertGreaterEqual(complex_msg["confidence"], simple["confidence"])

    # Test 20: Thai and English mixed task
    def test_mixed_language_task(self):
        """Test task with mixed Thai and English."""
        result = self.analyzer.analyze(
            "สร้างโปรเจค Python ที่มี API และ Database"
        )
        self.assertGreaterEqual(result["score"], 6)
        self.assertGreaterEqual(result["factors"]["technical_terms"], 2)


class TestAnalyzerPerformance(unittest.TestCase):
    """Performance-related tests."""

    def test_analysis_speed(self):
        """Test that analysis completes within 100ms."""
        import time

        analyzer = TaskAnalyzer()
        message = "สร้าง web app ร้านค้าใช้ React + Node.js + Database ครบวงจร"

        start_time = time.time()
        for _ in range(100):  # Run 100 times
            analyzer.analyze(message)
        end_time = time.time()

        avg_time = (end_time - start_time) / 100
        print(f"\nAverage analysis time: {avg_time * 1000:.2f}ms")
        self.assertLess(avg_time * 1000, 100)  # Less than 100ms


if __name__ == "__main__":
    unittest.main(verbosity=2)
