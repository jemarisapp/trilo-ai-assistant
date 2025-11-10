"""
Command Bridge
Bridges natural language to existing bot commands
"""

from typing import Optional, Dict, List


def detect_command_intent(user_message: str) -> Optional[Dict]:
    """
    Detect if user wants to execute a bot command
    
    Args:
        user_message: User's message text
        
    Returns:
        Dictionary with command info if detected, None otherwise
    """
    message_lower = user_message.lower()
    
    # Command mappings (can be expanded)
    command_patterns = {
        'records': {
            'keywords': ['record', 'standings', 'wins', 'losses', 'stats'],
            'command': 'records view'
        },
        'matchups': {
            'keywords': ['matchup', 'game', 'schedule', 'who am i playing'],
            'command': 'matchups list-all'
        },
        'points': {
            'keywords': ['points', 'attribute', 'upgrade', 'skill points'],
            'command': 'points view'
        },
        'teams': {
            'keywords': ['team', 'who has', 'assignment'],
            'command': 'teams list-all'
        }
    }
    
    # Check for command intent
    for cmd_name, cmd_info in command_patterns.items():
        if any(keyword in message_lower for keyword in cmd_info['keywords']):
            return {
                'command': cmd_info['command'],
                'type': cmd_name,
                'confidence': 0.7  # Can be improved with better NLP
            }
    
    return None


def map_natural_language_to_command(query: str) -> Optional[str]:
    """
    Map natural language query to bot command
    
    Args:
        query: Natural language query
        
    Returns:
        Command name if mapped, None otherwise
    """
    intent = detect_command_intent(query)
    return intent['command'] if intent else None


def format_command_suggestion(command: str, description: str = "") -> str:
    """
    Format a command suggestion for the user
    
    Args:
        command: Command name
        description: Optional description
        
    Returns:
        Formatted suggestion string
    """
    suggestion = f"💡 You can also use `/{command}`"
    if description:
        suggestion += f" to {description}"
    suggestion += "."
    return suggestion

