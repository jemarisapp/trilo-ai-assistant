"""
Training Examples for AI Query Classification
Provides few-shot learning examples to ensure consistent interpretation
"""

from typing import Dict, List


QUERY_CLASSIFICATION_EXAMPLES = """
# Training Examples for Query Classification

## Team Ownership Queries (command_execute)
- "who has Clemson" → Execute: /teams who-has team:Clemson
- "who has Clemson?" → Execute: /teams who-has team:Clemson
- "who owns Oregon" → Execute: /teams who-has team:Oregon
- "who's got Alabama" → Execute: /teams who-has team:Alabama
- "who is Clemson" → Execute: /teams who-has team:Clemson
- "who got Texas" → Execute: /teams who-has team:Texas

## Matchup Queries (command_help or user_specific)
- "what are my matchups" → User-specific matchup check
- "who do I play" → User-specific matchup check
- "show matchups for Week 1" → Command help: /matchups list-all
- "list all matchups" → Command help: /matchups list-all

## Points Queries (user_specific)
- "how many points do I have" → User-specific points check
- "check my points" → User-specific points check
- "what's my point balance" → User-specific points check

## Record Queries (user_specific)
- "what's my record" → User-specific record check
- "check my wins and losses" → User-specific record check
- "am I winning" → User-specific record check

## Setup Questions (setup_help)
- "how do I setup stream notifications" → Setup help
- "how to configure teams" → Setup help
- "getting started with bot" → Setup help

## General Conversation (general)
- "hey how's it going" → General conversation
- "what's new" → General conversation
- "thanks" → General conversation

## Command Execution (command_execute)
- "create matchups from this image" → Execute: /matchups create-from-image
- "delete Week 1" → Execute: /matchups delete
- "tag users in Week 1" → Execute: /matchups tag-users

CRITICAL RULES:
1. "who has [team]" ALWAYS means check team ownership, regardless of punctuation
2. "who is [team]" when [team] is capitalized means team ownership
3. Variations like "who's got", "who owns" all mean the same thing
4. Punctuation (?, !, .) does not change the meaning of the query
"""


TEAM_OWNERSHIP_VARIATIONS = [
    "who has {team}",
    "who has {team}?",
    "who owns {team}",
    "who owns {team}?",
    "who's got {team}",
    "who got {team}",
    "whos got {team}",
    "who is {team}",
    "who is {team}?",
]


def get_few_shot_examples(query_type: str) -> str:
    """
    Get relevant few-shot examples based on query type
    
    Args:
        query_type: Type of query to get examples for
        
    Returns:
        String with formatted examples
    """
    examples = {
        "team_ownership": """
Examples of team ownership queries:
- "who has Clemson" → Check who owns Clemson team
- "who has Clemson?" → Check who owns Clemson team (same as above)
- "who owns Oregon" → Check who owns Oregon team
- "who is Alabama" → Check who owns Alabama team

These should ALL be handled the same way regardless of punctuation.
""",
        
        "command_execute": """
Examples of command execution requests:
- "create matchups from this image" → /matchups create-from-image
- "delete Week 1 matchups" → /matchups delete category:Week 1
- "tag users in Week 2" → /matchups tag-users category:Week 2
- "announce Week 3 advance on Monday" → /message announce-advance
""",
        
        "setup_help": """
Examples of setup questions:
- "how do I set up my league" → Provide full setup guide
- "how to configure stream notifications" → Explain stream settings
- "how do I assign teams" → Explain /teams assign-user
- "getting started" → Provide quick start guide
""",
        
        "user_specific": """
Examples of user-specific queries:
- "what are my matchups" → Show user's current matchups
- "how many points do I have" → Show user's attribute points
- "what's my record" → Show user's win-loss record
- "who do I play" → Show user's upcoming matchups
""",
    }
    
    return examples.get(query_type, "")


def get_intent_classification_context() -> str:
    """
    Get context for intent classification to improve consistency
    
    Returns:
        String with classification guidelines
    """
    return """
INTENT CLASSIFICATION GUIDELINES:

1. TEAM OWNERSHIP QUERIES
   Pattern: "who has/owns/is [Team Name]"
   Intent: command_execute (execute /teams who-has)
   Key indicators:
   - Starts with "who"
   - Followed by "has", "owns", "got", "is"
   - Ends with a team name (often capitalized)
   - Punctuation doesn't matter: "who has X" = "who has X?" = "who has X."

2. MATCHUP QUERIES
   Pattern: "show/list/what matchups"
   Intent: command_help OR user_specific
   - "my matchups" → user_specific
   - "matchups for Week 1" → command_help

3. POINTS QUERIES
   Pattern: "how many points", "check points", "my points"
   Intent: user_specific
   
4. SETUP QUESTIONS
   Pattern: "how do I", "how to", "setup", "configure", "getting started"
   Intent: setup_help

5. COMMAND EXECUTION
   Pattern: "create", "delete", "tag", "announce"
   Intent: command_execute

6. GENERAL CONVERSATION
   Pattern: Greetings, thanks, questions without clear intent
   Intent: general

CONSISTENCY RULE:
Queries that differ ONLY in punctuation or capitalization should receive the SAME classification.
"""


def validate_query_consistency(queries: List[str], expected_intent: str) -> Dict:
    """
    Validate that similar queries produce consistent results
    
    Args:
        queries: List of similar queries that should have same intent
        expected_intent: The intent they should all map to
        
    Returns:
        Dictionary with validation results
    """
    # This would be used for testing/validation
    # Not called during runtime, but useful for development
    return {
        "queries": queries,
        "expected_intent": expected_intent,
        "test": "consistency_check"
    }


# Consistency test cases
CONSISTENCY_TEST_CASES = [
    {
        "variations": [
            "who has Clemson",
            "who has Clemson?",
            "who has Clemson.",
            "Who has Clemson",
            "WHO HAS CLEMSON",
        ],
        "expected_intent": "command_execute",
        "expected_action": "/teams who-has team:Clemson"
    },
    {
        "variations": [
            "who owns Oregon",
            "who owns Oregon?",
            "who's got Oregon",
            "whos got Oregon",
            "who is Oregon",
        ],
        "expected_intent": "command_execute",
        "expected_action": "/teams who-has team:Oregon"
    },
    {
        "variations": [
            "what are my matchups",
            "what are my matchups?",
            "show my matchups",
            "show me my matchups",
        ],
        "expected_intent": "user_specific",
        "expected_action": "Show user's matchups"
    },
]


def get_training_prompt_addition() -> str:
    """
    Get additional context to add to AI prompts for better consistency
    
    Returns:
        String to append to prompts
    """
    return """

IMPORTANT: Normalize queries before classifying:
- Remove punctuation at the end (?, !, .)
- Convert to lowercase for comparison
- Treat "who has X", "who owns X", "who's got X", "who is X" as identical
- Focus on the core question, not the exact wording

Examples of IDENTICAL queries (should get same response):
- "who has Clemson" = "who has Clemson?" = "Who has Clemson"
- "what's my record" = "what is my record" = "whats my record?"
"""




