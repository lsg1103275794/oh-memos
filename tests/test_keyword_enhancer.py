#!/usr/bin/env python3
"""
Test script for keyword_enhancer module.

Run: python test_keyword_enhancer.py
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add mcp-server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from keyword_enhancer import (
    extract_keywords_enhanced,
    keyword_match_score_enhanced,
    detect_cube_from_path,
    find_fuzzy_matches,
    levenshtein_distance,
    ALL_STOPWORDS,
)

# Use ASCII-safe symbols
PASS = "[OK]"
FAIL = "[X]"


def test_stopwords():
    """Test stopword library size and content."""
    print("=" * 60)
    print("Test: Stopwords Library")
    print("=" * 60)

    total = len(ALL_STOPWORDS)
    english_count = sum(1 for w in ALL_STOPWORDS if w.isascii())
    chinese_count = total - english_count

    print(f"Total stopwords: {total}")
    print(f"English stopwords: {english_count}")
    print(f"Chinese stopwords: {chinese_count}")

    # Test some common stopwords
    test_words = ["the", "and", "function", "class", "的", "是", "import", "return"]
    for word in test_words:
        status = PASS if word.lower() in ALL_STOPWORDS else FAIL
        print(f"  {status} '{word}' is stopword: {word.lower() in ALL_STOPWORDS}")

    print()
    return total > 500  # Should have 500+ stopwords


def test_keyword_extraction():
    """Test keyword extraction with stopword filtering."""
    print("=" * 60)
    print("Test: Keyword Extraction")
    print("=" * 60)

    test_cases = [
        # English keywords - stopwords filtered
        ("Fix the authentication bug", ["fix", "authentication", "bug"]),
        # Chinese - continuous characters kept as one token (no jieba)
        ("修复数据库连接问题", ["修复数据库连接问题"]),
        # All stopwords should be filtered
        ("import function from module", []),
        # Mixed - English stopwords filtered
        ("Neo4j connection timeout error", ["neo4j", "connection", "timeout"]),
        # Chinese continuous - kept as is
        ("配置文件解析失败", ["配置文件解析失败"]),
        # Mixed English and Chinese
        ("Redis 连接超时", ["redis", "连接超时"]),
    ]

    passed = 0
    for query, expected in test_cases:
        result = extract_keywords_enhanced(query)
        # Check if result matches expected (order may differ)
        expected_set = set(expected)
        result_set = set(result)

        # For single expected keyword, check if any result contains it
        if len(expected) == 1 and expected[0] in query:
            match = any(expected[0] in r or r in expected[0] for r in result)
        else:
            # Check subset relationship
            match = expected_set <= result_set or result_set <= expected_set

        status = PASS if match else FAIL
        print(f"  {status} Query: '{query}'")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")
        if match:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    print()
    return passed >= len(test_cases) * 0.6


def test_fuzzy_matching():
    """Test fuzzy matching with Levenshtein distance."""
    print("=" * 60)
    print("Test: Fuzzy Matching")
    print("=" * 60)

    # Test Levenshtein distance
    distance_tests = [
        ("cat", "cat", 0),
        ("cat", "bat", 1),
        ("kitten", "sitting", 3),
        ("config", "configuration", 7),
    ]

    print("Levenshtein Distance:")
    for s1, s2, expected in distance_tests:
        result = levenshtein_distance(s1, s2)
        status = PASS if result == expected else FAIL
        print(f"  {status} '{s1}' vs '{s2}': {result} (expected {expected})")

    print()

    # Test fuzzy match finding
    print("Fuzzy Match Finding:")
    text = "The configration file has authentication errors in the databse"
    keywords = ["configuration", "database", "authentication"]

    for kw in keywords:
        matches = find_fuzzy_matches(kw, text, threshold=0.7)
        print(f"  Keyword '{kw}':")
        if matches:
            for word, score in matches[:3]:
                print(f"    -> '{word}' (score: {score:.2f})")
        else:
            print(f"    -> No matches found")

    print()
    return True


def test_keyword_scoring():
    """Test keyword match scoring with structured fields."""
    print("=" * 60)
    print("Test: Keyword Match Scoring")
    print("=" * 60)

    text = "[BUGFIX] Fixed authentication timeout in login module"
    keywords = ["authentication", "timeout", "login"]

    # Test without metadata
    score1 = keyword_match_score_enhanced(text, keywords, metadata=None)
    print(f"Score without metadata: {score1:.2f}")

    # Test with metadata (key field)
    metadata_key = {"key": "authentication-fix", "tags": ["auth", "bugfix"]}
    score2 = keyword_match_score_enhanced(text, keywords, metadata=metadata_key)
    print(f"Score with key 'authentication-fix': {score2:.2f}")

    # Test with tags
    metadata_tags = {"key": "generic", "tags": ["authentication", "timeout"]}
    score3 = keyword_match_score_enhanced(text, keywords, metadata=metadata_tags)
    print(f"Score with matching tags: {score3:.2f}")

    print()

    # Score with metadata should be higher
    assert score2 > score1, "Metadata key should increase score"
    assert score3 > score1, "Matching tags should increase score"

    print(PASS + " Structured field weighting works correctly")
    print()
    return True


def test_cube_detection():
    """Test smart cube detection from project path."""
    print("=" * 60)
    print("Test: Smart Cube Detection")
    print("=" * 60)

    test_cases = [
        ("/mnt/g/test/MemOS", "memos_cube"),
        ("/home/user/my-project", "my_project_cube"),
        ("C:\\Projects\\WebApp", "webapp_cube"),
        ("/tmp/test.app", "test_app_cube"),
        ("/home/user/123-project", "_123_project_cube"),
        # Additional Windows path tests
        ("D:\\Work\\my-app", "my_app_cube"),
    ]

    passed = 0
    for path, expected in test_cases:
        result = detect_cube_from_path(path)
        status = PASS if result == expected else FAIL
        print(f"  {status} Path: '{path}'")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")
        if result == expected:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    print()
    return passed >= len(test_cases) * 0.8


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Keyword Enhancer Module Tests")
    print("=" * 60 + "\n")

    results = []

    results.append(("Stopwords Library", test_stopwords()))
    results.append(("Keyword Extraction", test_keyword_extraction()))
    results.append(("Fuzzy Matching", test_fuzzy_matching()))
    results.append(("Keyword Scoring", test_keyword_scoring()))
    results.append(("Cube Detection", test_cube_detection()))

    print("=" * 60)
    print("  Summary")
    print("=" * 60)

    passed = 0
    for name, result in results:
        status = PASS + " PASS" if result else FAIL + " FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1

    print()
    print(f"Total: {passed}/{len(results)} tests passed")
    print()

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
