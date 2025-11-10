"""
Query Analysis and Intent Detection
Analyzes user queries to determine intent and required actions
"""

from typing import Dict, List, Literal


def detect_search_intent(query: str) -> bool:
    """
    Detect if query requires searching past messages across channels
    
    Args:
        query: User's query text
        
    Returns:
        True if query requires cross-channel search
    """
    search_indicators = [
        "who won", "what happened", "when did", "who was",
        "season", "week", "championship", "natty", "champ",
        "last year", "previous", "earlier", "before",
        "history", "past", "earlier"
    ]
    
    # Questions that should trigger search (including advance questions)
    search_questions = [
        "when is advance", "when's advance", "when advance",
        "next advance", "advance time", "advance schedule",
        "when is the advance", "when's the advance"
    ]
    
    query_lower = query.lower()
    
    # Check for advance-related questions (should always search)
    if any(phrase in query_lower for phrase in search_questions):
        return True
    
    # Check for question words + past tense indicators
    has_question = any(word in query_lower for word in ["who", "what", "when", "where", "how"])
    has_past_tense = any(word in query_lower for word in search_indicators)
    
    return has_question and has_past_tense


def detect_summary_intent(query: str) -> bool:
    """
    Detect if user wants a summary of past messages
    
    Args:
        query: User's query text
        
    Returns:
        True if user wants a summary
    """
    summary_keywords = [
        "summarize", "summary", "recap", "catch up",
        "what did i miss", "what happened", "what was said"
    ]
    
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in summary_keywords)


def extract_keywords(query: str) -> List[str]:
    """
    Extract search keywords from query
    
    Args:
        query: User's query text
        
    Returns:
        List of keywords
    """
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were",
        "what", "who", "when", "where", "how", "why", "did", "does", "do"
    }
    
    # Simple keyword extraction (can be enhanced with NLP)
    words = query.lower().split()
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return keywords


def classify_query_type(query: str) -> Literal["search", "summary", "command_help", "matchups", "conversation"]:
    """
    Classify the type of query
    
    Args:
        query: User's query text
        
    Returns:
        Query type classification
    """
    query_lower = query.lower()
    
    # Check for command help requests first
    command_help_keywords = [
        "how do i", "how to", "how can i", "how does", "how do you",
        "what command", "what's the command", "what is the command",
        "command for", "use command", "run command",
        "spend points", "spend my points", "use points", "use my points",
        "help with", "help me", "tell me how"
    ]
    if any(keyword in query_lower for keyword in command_help_keywords):
        return "command_help"
    
    # Check for matchup questions (should read channels directly, not search messages)
    # BUT exclude delete/remove commands (those should be handled by command_execute)
    delete_keywords = ["delete", "remove", "clear"]
    if any(keyword in query_lower for keyword in delete_keywords):
        # Don't classify as matchups if it's a delete command
        pass
    else:
        matchup_keywords = ["matchup", "matchups", "this week", "week", "games", "schedule"]
        if any(keyword in query_lower for keyword in matchup_keywords):
            # But only if it's asking about current/upcoming matchups, not historical
            if not any(word in query_lower for word in ["last", "past", "previous", "season", "won"]):
                return "matchups"
    
    # Check for advance questions first (should always search)
    advance_keywords = ["advance", "next advance", "advance time", "advance schedule"]
    if any(keyword in query_lower for keyword in advance_keywords):
        return "search"
    
    if detect_search_intent(query):
        return "search"
    elif detect_summary_intent(query):
        return "summary"
    else:
        return "conversation"


def estimate_query_complexity(query: str) -> str:
    """
    Estimate query complexity to determine which AI model to use
    
    Args:
        query: User's query text
        
    Returns:
        "simple" or "complex"
    """
    # Simple queries: short, direct questions
    # Complex queries: require reasoning, multiple sources, synthesis
    
    query_lower = query.lower()
    
    # Complex indicators
    complex_indicators = [
        "compare", "analyze", "why", "explain", "how does",
        "relationship", "difference", "similar"
    ]
    
    if any(indicator in query_lower for indicator in complex_indicators):
        return "complex"
    
    # Long queries are likely complex
    if len(query.split()) > 15:
        return "complex"
    
    return "simple"

