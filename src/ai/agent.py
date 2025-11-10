"""
Agent System for Query Classification and Routing
Classifies user queries into different types and routes them appropriately
"""

from typing import Literal, Dict, Optional
import os
from pathlib import Path


def classify_query_intent(query: str) -> Literal["command_help", "command_execute", "user_specific", "league_specific", "general"]:
    """
    Classify the intent of a user query using an agentic approach
    
    Args:
        query: User's query text
        
    Returns:
        Query intent classification
    """
    query_lower = query.lower()
    
    # Command execution indicators (user wants to DO something, not learn how)
    command_execute_keywords = [
        "show me", "show my", "display", "get my", "check my",
        "what's my", "what is my", "tell me my",
        "who has", "who owns", "list", "show all", "view all",
        "give me", "i want to see", "i need to see",
        "request", "spend", "use points", "upgrade", "i want to",
        "spend them", "use them", "allocate", "spend my",
        "create matchups", "create from image", "extract matchups", "process image",
        "delete matchups", "delete categories", "remove matchups", "remove categories",
        "delete category", "remove category", "clear matchups", "delete week", "remove week",
        "tag users", "tag players", "notify users", "mention users",
        "announce advance", "announce week", "advance announcement", "notify advance"
    ]
    
    # Command help indicators (user wants to LEARN how)
    command_help_keywords = [
        "how do i", "how to", "how can i", "how does", "how do you",
        "what command", "what's the command", "what is the command",
        "command for", "use command", "run command",
        "help with", "help me", "tell me how"
    ]
    
    # User-specific indicators (about the user themselves)
    user_specific_keywords = [
        "my points", "my team", "my record", "my matchups",
        "i have", "i own", "my balance", "my requests",
        "how many points do i", "what's my", "what is my",
        "do i have", "am i", "my upgrade"
    ]
    
    # League-specific indicators (about the league in general)
    league_specific_keywords = [
        "standings", "all teams", "all records", "league standings",
        "who has", "which team", "all matchups", "league matchups",
        "everyone", "all users", "all players", "league records"
    ]
    
    # Check for command execution first (user wants to DO something)
    if any(keyword in query_lower for keyword in command_execute_keywords):
        return "command_execute"
    
    # Check for command help (user wants to LEARN how)
    if any(keyword in query_lower for keyword in command_help_keywords):
        return "command_help"
    
    # Check for user-specific queries (but prioritize execution if they want to see data)
    if any(keyword in query_lower for keyword in user_specific_keywords):
        # If they're asking to see their data, it's execution
        if any(exec_keyword in query_lower for exec_keyword in ["show", "get", "check", "what's", "what is", "tell me"]):
            return "command_execute"
        return "user_specific"
    
    # Check for league-specific queries
    if any(keyword in query_lower for keyword in league_specific_keywords):
        return "league_specific"
    
    # Default to general conversation
    return "general"


def extract_command_topic(query: str) -> Optional[str]:
    """
    Extract the specific command or topic the user is asking about
    
    Args:
        query: User's query text
        
    Returns:
        Command topic (e.g., "attributes request", "points", "matchups") or None
    """
    query_lower = query.lower()
    
    # Map keywords to command topics
    topic_mapping = {
        "points": ["points", "attribute points", "attribute point"],
        "attributes request": ["spend points", "use points", "request upgrade", "upgrade player", "request attribute"],
        "attributes my-points": ["my points", "check points", "view points", "see points", "how many points"],
        "attributes give": ["give points", "award points", "give attribute"],
        "attributes approve": ["approve request", "approve upgrade", "approve"],
        "attributes deny": ["deny request", "deny upgrade", "deny"],
        "teams assign": ["assign team", "assign user", "assign team to user"],
        "teams who-has": ["who has", "who owns", "which user has"],
        "matchups create": ["create matchup", "create matchups", "make matchup"],
        "matchups list": ["list matchups", "view matchups", "show matchups", "all matchups"],
        "records check": ["check record", "view record", "see record", "team record"],
        "records set": ["set record", "update record", "change record"],
        "message custom": ["send message", "custom message", "announce"],
        "message announce-advance": ["announce advance", "advance announcement"],
        "settings": ["settings", "configure", "set setting"],
        "help": ["help", "how to use", "commands"]
    }
    
    # Find matching topic
    for topic, keywords in topic_mapping.items():
        if any(keyword in query_lower for keyword in keywords):
            return topic
    
    return None


def get_command_category(topic: Optional[str]) -> Optional[str]:
    """
    Get the command category from a topic
    
    Args:
        topic: Command topic (e.g., "attributes request")
        
    Returns:
        Category name (e.g., "attributes", "teams", "matchups") or None
    """
    if not topic:
        return None
    
    if topic.startswith("attributes"):
        return "attributes"
    elif topic.startswith("teams"):
        return "teams"
    elif topic.startswith("matchups"):
        return "matchups"
    elif topic.startswith("records"):
        return "records"
    elif topic.startswith("message"):
        return "message"
    elif topic.startswith("settings"):
        return "settings"
    elif topic.startswith("admin"):
        return "admin"
    elif topic.startswith("help"):
        return "help"
    
    return None

