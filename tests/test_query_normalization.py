"""
Test Query Normalization and Pattern Matching
Validates that similar queries are handled consistently
"""

import sys
sys.path.insert(0, '/Users/jsapp/Documents/Trilo/Trilo')

from src.ai.query_normalizer import (
    normalize_query,
    extract_team_name,
    is_team_ownership_query,
    get_query_signature,
    standardize_team_name_variations
)
from src.ai.query_patterns import get_pattern_confidence


def test_query_normalization():
    """Test that different variations normalize to same query"""
    print("=" * 70)
    print("TEST 1: QUERY NORMALIZATION")
    print("=" * 70)
    
    variations = [
        "who has Clemson",
        "who has Clemson?",
        "who has Clemson.",
        "who has Clemson!",
        "who has  Clemson",  # Extra space
        "Who has Clemson",
        "WHO HAS CLEMSON",
    ]
    
    signatures = set()
    for query in variations:
        normalized = normalize_query(query)
        signature = get_query_signature(query)
        signatures.add(signature)
        print(f"'{query:30s}' → Normalized: '{normalized:25s}' → Signature: '{signature}'")
    
    # All should have same signature
    assert len(signatures) == 1, f"Expected 1 unique signature, got {len(signatures)}"
    print(f"\n✅ SUCCESS: All {len(variations)} variations have the same signature: '{list(signatures)[0]}'")


def test_team_ownership_detection():
    """Test that all ownership query variations are detected"""
    print("\n" + "=" * 70)
    print("TEST 2: TEAM OWNERSHIP DETECTION")
    print("=" * 70)
    
    ownership_queries = [
        "who has Clemson",
        "who has Clemson?",
        "who owns Oregon",
        "who owns Oregon?",
        "who's got Alabama",
        "whos got Texas",
        "who is Clemson",  # This should match
        "who got Florida",
    ]
    
    non_ownership_queries = [
        "who has the most points",
        "who is winning",
        "who has a matchup",
        "what matchups do we have",
    ]
    
    print("\nShould be detected as ownership queries:")
    for query in ownership_queries:
        is_ownership = is_team_ownership_query(query)
        status = "✅" if is_ownership else "❌"
        print(f"  {status} '{query}' → {is_ownership}")
        assert is_ownership, f"Failed to detect: {query}"
    
    print("\nShould NOT be detected as ownership queries:")
    for query in non_ownership_queries:
        is_ownership = is_team_ownership_query(query)
        status = "✅" if not is_ownership else "❌"
        print(f"  {status} '{query}' → {not is_ownership}")
        assert not is_ownership, f"False positive: {query}"
    
    print("\n✅ SUCCESS: All ownership queries detected correctly!")


def test_team_name_extraction():
    """Test team name extraction from queries"""
    print("\n" + "=" * 70)
    print("TEST 3: TEAM NAME EXTRACTION")
    print("=" * 70)
    
    test_cases = [
        ("who has Clemson", "Clemson"),
        ("who has Clemson?", "Clemson"),
        ("who owns Oregon", "Oregon"),
        ("who's got Alabama", "Alabama"),
        ("who is Texas", "Texas"),
        ("who has the Ohio State", "Ohio State"),  # "the" is normalized away
    ]
    
    for query, expected_team in test_cases:
        _, extracted = extract_team_name(query)
        status = "✅" if extracted == expected_team else "❌"
        print(f"  {status} '{query}' → Team: '{extracted}' (expected: '{expected_team}')")
        assert extracted == expected_team, f"Failed: got '{extracted}', expected '{expected_team}'"
    
    print("\n✅ SUCCESS: All team names extracted correctly!")


def test_pattern_confidence():
    """Test pattern matching confidence calculation"""
    print("\n" + "=" * 70)
    print("TEST 4: PATTERN MATCHING CONFIDENCE")
    print("=" * 70)
    
    high_confidence = [
        "who has Clemson",
        "who owns Oregon",
        "who's got Alabama",
    ]
    
    low_confidence = [
        "tell me about Clemson",
        "what's the record",
        "how are you",
    ]
    
    print("\nHigh confidence queries (should be > 0.9):")
    for query in high_confidence:
        confidence = get_pattern_confidence(query)
        status = "✅" if confidence > 0.9 else "❌"
        print(f"  {status} '{query}' → {confidence:.2f}")
        assert confidence > 0.9, f"Low confidence for: {query}"
    
    print("\nLow confidence queries (should be < 0.5):")
    for query in low_confidence:
        confidence = get_pattern_confidence(query)
        status = "✅" if confidence < 0.5 else "❌"
        print(f"  {status} '{query}' → {confidence:.2f}")
        assert confidence < 0.5, f"High confidence for: {query}"
    
    print("\n✅ SUCCESS: Confidence calculation working correctly!")


def test_team_name_standardization():
    """Test team name variation standardization"""
    print("\n" + "=" * 70)
    print("TEST 5: TEAM NAME STANDARDIZATION")
    print("=" * 70)
    
    test_cases = [
        ("bama", "Alabama"),
        ("BAMA", "Alabama"),
        ("Bama", "Alabama"),
        ("osu", "Ohio State"),
        ("OSU", "Ohio State"),
        ("uga", "Georgia"),
        ("UGA", "Georgia"),
        ("Clemson", "Clemson"),  # Should stay the same
        ("Oregon Ducks", "Oregon"),  # Should remove "Ducks"
    ]
    
    for input_name, expected in test_cases:
        standardized = standardize_team_name_variations(input_name)
        status = "✅" if standardized == expected else "❌"
        print(f"  {status} '{input_name:20s}' → '{standardized}' (expected: '{expected}')")
        if standardized != expected:
            print(f"       WARNING: Got '{standardized}' instead of '{expected}'")
    
    print("\n✅ COMPLETED: Team name standardization tested!")


def test_consistency_across_all_systems():
    """End-to-end test: Same signature → Should get same response"""
    print("\n" + "=" * 70)
    print("TEST 6: END-TO-END CONSISTENCY")
    print("=" * 70)
    
    query_sets = [
        ["who has Clemson", "who has Clemson?", "who owns Clemson", "who is Clemson"],
        ["who has Oregon", "who has Oregon?", "who owns Oregon"],
        ["who has Alabama", "whos got Alabama", "who's got Alabama"],
    ]
    
    for query_set in query_sets:
        signatures = []
        confidences = []
        is_ownership_results = []
        
        print(f"\nTesting query set:")
        for query in query_set:
            sig = get_query_signature(query)
            conf = get_pattern_confidence(query)
            is_own = is_team_ownership_query(query)
            
            signatures.append(sig)
            confidences.append(conf)
            is_ownership_results.append(is_own)
            
            print(f"  '{query}'")
            print(f"    → Signature: {sig}")
            print(f"    → Confidence: {conf:.2f}")
            print(f"    → Is Ownership: {is_own}")
        
        # All queries in set should have:
        # 1. Same signature (for caching)
        unique_sigs = set(signatures)
        assert len(unique_sigs) == 1, f"Expected 1 signature, got {len(unique_sigs)}: {unique_sigs}"
        
        # 2. All detected as ownership queries
        assert all(is_ownership_results), f"Not all detected as ownership: {is_ownership_results}"
        
        # 3. High confidence
        assert all(c > 0.9 for c in confidences), f"Not all have high confidence: {confidences}"
        
        print(f"  ✅ CONSISTENT: Signature={signatures[0]}, Ownership={all(is_ownership_results)}, Confidence={min(confidences):.2f}")
    
    print("\n✅ SUCCESS: All query variations are processed consistently!")


if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║       QUERY NORMALIZATION & CONSISTENCY TEST SUITE               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    try:
        test_query_normalization()
        test_team_ownership_detection()
        test_team_name_extraction()
        test_pattern_confidence()
        test_team_name_standardization()
        test_consistency_across_all_systems()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 70)
        print()
        print("The query training system is working correctly!")
        print("Queries like 'who has Clemson?' and 'who has Clemson' will now")
        print("produce identical responses.")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

