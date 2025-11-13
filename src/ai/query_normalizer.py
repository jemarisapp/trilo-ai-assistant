"""
Query Normalizer
Standardizes user queries to ensure consistent processing
"""

import re
from typing import Tuple


def normalize_query(query: str) -> str:
    """
    Normalize a query to standard form for consistent processing
    
    Args:
        query: Raw user query
        
    Returns:
        Normalized query string
    """
    # Convert to lowercase for processing (but preserve for display)
    normalized = query.strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Standardize punctuation patterns
    # "who has X?" → "who has X"
    # "who has X." → "who has X"
    normalized = re.sub(r'[?.!]+$', '', normalized)
    
    # Standardize common question variations
    patterns = [
        # "who's got X" → "who has X"
        (r'\bwho\'?s got\b', 'who has'),
        (r'\bwho\'?s gotten\b', 'who has'),
        
        # "who owns X" → "who has X"
        (r'\bwho owns\b', 'who has'),
        
        # "who is X" (when asking about team ownership) → "who has X"
        # This is tricky - "who is X" could mean "what team is user X" OR "who owns team X"
        # We'll handle this in pattern matching
        
        # Standardize article usage
        (r'\bwho has the\b', 'who has'),
        (r'\bwho owns the\b', 'who has'),
        
        # "which user has" → "who has"
        (r'\bwhich user has\b', 'who has'),
        (r'\bwhat user has\b', 'who has'),
    ]
    
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    # Strip again after replacements
    normalized = normalized.strip()
    
    return normalized


def extract_team_name(query: str) -> Tuple[str, str]:
    """
    Extract team name from a query like "who has Clemson"
    
    Returns:
        Tuple of (normalized_query, team_name)
    """
    # Normalize first
    normalized = normalize_query(query)
    
    # Common patterns for team ownership queries
    patterns = [
        r'who has (.+)',
        r'who owns (.+)',
        r'who is (.+)',  # "who is Clemson" asking about ownership
        r'who got (.+)',
        r'whos got (.+)',
        r'who\'s got (.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            team_name = match.group(1).strip()
            # Remove trailing punctuation from team name
            team_name = re.sub(r'[?.!,]+$', '', team_name)
            return normalized, team_name
    
    return normalized, ""


def is_team_ownership_query(query: str) -> bool:
    """
    Detect if query is asking about team ownership
    
    Examples:
        "who has Clemson" → True
        "who has Clemson?" → True
        "who is Clemson" → True
        "who owns Oregon" → True
        "who has the most points" → False
        "who is winning" → False
    """
    # Normalize first to remove punctuation
    normalized = normalize_query(query).lower()
    
    # Ownership query patterns (case-insensitive)
    ownership_patterns = [
        r'^who has [a-z0-9\s&\-\']+$',
        r'^who owns [a-z0-9\s&\-\']+$',
        r'^who got [a-z0-9\s&\-\']+$',
        r'^whos got [a-z0-9\s&\-\']+$',
        r'^who\'s got [a-z0-9\s&\-\']+$',
        r'^who is [a-z0-9\s&\-\']+$',  # "who is Clemson"
    ]
    
    # Exclude queries that are clearly NOT about team ownership FIRST
    # Note: These patterns match AFTER normalization (e.g., "the" is removed)
    exclusion_patterns = [
        r'who has (?:the )?most',  # "who has most" or "who has the most"
        r'who has more',
        r'who is winning',
        r'who is ahead',
        r'who is leading',
        r'who has (?:a )?matchup',  # "who has matchup" or "who has a matchup"
        r'who has games',
    ]
    
    for pattern in exclusion_patterns:
        if re.search(pattern, normalized):
            return False
    
    # Check if it matches ownership patterns
    for pattern in ownership_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return True
    
    return False


def get_query_signature(query: str) -> str:
    """
    Generate a signature for query caching
    Queries with same signature should produce same result
    
    Examples:
        "who has Clemson?" → "who_has_clemson"
        "who has Clemson" → "who_has_clemson"
        "Who owns Clemson?" → "who_has_clemson"
        "who is Clemson" → "who_has_clemson" (normalized to "who has")
    """
    normalized = normalize_query(query).lower()
    
    # Additional normalization for signature consistency
    # All ownership queries should map to the same signature pattern
    normalized = re.sub(r'\bwho\s+(?:owns|is|got|\'s\s+got|s\s+got)\b', 'who has', normalized)
    
    # Replace spaces with underscores
    signature = re.sub(r'\s+', '_', normalized)
    
    # Remove special characters
    signature = re.sub(r'[^a-z0-9_]', '', signature)
    
    return signature


def detect_query_intent_from_structure(query: str) -> str:
    """
    Detect intent based on query structure patterns
    More reliable than AI for common patterns
    
    Returns:
        Intent string: "team_ownership", "matchup_info", "points_check", etc.
        Or "" if no clear pattern detected
    """
    normalized = normalize_query(query).lower()
    
    # Team ownership queries
    if is_team_ownership_query(query):
        return "team_ownership"
    
    # Matchup queries
    matchup_patterns = [
        r'matchups? (?:for|in|of)',
        r'show matchups?',
        r'list matchups?',
        r'what matchups?',
        r'who plays? who',
        r'who (?:am i|do i) play',
    ]
    for pattern in matchup_patterns:
        if re.search(pattern, normalized):
            return "matchup_info"
    
    # Points queries
    points_patterns = [
        r'how many points? (?:do|does)',
        r'check (?:my )?points?',
        r'what\'?s? my points?',
        r'points? check',
    ]
    for pattern in points_patterns:
        if re.search(pattern, normalized):
            return "points_check"
    
    # Record queries
    record_patterns = [
        r'what\'?s? (?:my )?record',
        r'check (?:my )?record',
        r'(?:my )?win-?loss',
        r'how many (?:wins|losses)',
    ]
    for pattern in record_patterns:
        if re.search(pattern, normalized):
            return "record_check"
    
    # No clear pattern
    return ""


def standardize_team_name_variations(team_name: str) -> str:
    """
    Standardize common team name variations
    
    Examples:
        "clemson" → "Clemson"
        "oregon ducks" → "Oregon"
        "bama" → "Alabama"
    """
    team_name = team_name.strip()
    
    # Common abbreviations and nicknames
    team_variations = {
        # CFB
        'bama': 'Alabama',
        'uga': 'Georgia',
        'osu': 'Ohio State',
        'ou': 'Oklahoma',
        'usc': 'USC',
        'tamu': 'Texas A&M',
        'a&m': 'Texas A&M',
        'texas a&m': 'Texas A&M',
        'lsu': 'LSU',
        'fsu': 'Florida State',
        'uf': 'Florida',
        'um': 'Miami',
        'the u': 'Miami',
        'nd': 'Notre Dame',
        'psu': 'Penn State',
        'msu': 'Michigan State',
        'vt': 'Virginia Tech',
        'gt': 'Georgia Tech',
        
        # NFL
        'niners': '49ers',
        'bucs': 'Buccaneers',
        'pats': 'Patriots',
        'hawks': 'Seahawks',
        'pack': 'Packers',
        'fins': 'Dolphins',
        'cards': 'Cardinals',
        'skins': 'Commanders',
        'football team': 'Commanders',
    }
    
    # Check if it's a known abbreviation
    team_lower = team_name.lower()
    if team_lower in team_variations:
        return team_variations[team_lower]
    
    # Remove common suffixes (but keep them if they're the only word)
    words = team_name.split()
    if len(words) > 1:
        suffixes = ['ducks', 'tigers', 'buckeyes', 'crimson tide', 'bulldogs', 
                   'longhorns', 'bears', 'wildcats', 'trojans', 'spartans',
                   'packers', 'cowboys', 'patriots', 'eagles', 'giants']
        
        # If last word(s) is a suffix, remove it
        for suffix in suffixes:
            suffix_words = suffix.split()
            if words[-len(suffix_words):] == suffix_words:
                team_name = ' '.join(words[:-len(suffix_words)])
                break
    
    # Capitalize each word
    return team_name.title()

