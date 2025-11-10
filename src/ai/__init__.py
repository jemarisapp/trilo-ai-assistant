"""
Trilo AI Module
Provides natural language conversation, context retrieval, and cross-channel search capabilities
"""

from .context_retriever import (
    get_user_context,
    get_league_context,
    get_user_matchups,
    can_user_see_channel
)

from .conversation import handle_ai_conversation

__all__ = [
    'get_user_context',
    'get_league_context',
    'get_user_matchups',
    'can_user_see_channel',
    'handle_ai_conversation',
]

