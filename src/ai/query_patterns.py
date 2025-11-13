"""
Query Pattern Matcher
Routes common queries directly without AI classification for consistency
"""

import discord
from typing import Optional, Tuple
from .query_normalizer import normalize_query, extract_team_name, is_team_ownership_query
from utils.utils import get_db_connection, format_team_name, clean_team_key
from commands.settings import get_server_setting


async def try_direct_pattern_match(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Try to match query against known patterns and handle directly
    
    Returns:
        (handled, response) where:
        - handled: True if query was handled by pattern matching
        - response: Response string if handled, None otherwise
    """
    
    # Team ownership queries: "who has Clemson", "who owns Oregon", etc.
    if is_team_ownership_query(query):
        normalized, team_name = extract_team_name(query)
        if team_name:
            response = await handle_team_ownership_query(team_name, message.guild, server_id)
            return True, response
    
    # No pattern match
    return False, None


async def handle_team_ownership_query(
    team_name: str,
    guild: discord.Guild,
    server_id: str
) -> str:
    """
    Handle "who has X team" queries directly
    
    This bypasses AI to ensure consistent responses
    """
    try:
        # Clean and standardize team name
        team_key = clean_team_key(team_name)
        
        # Get league type
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        teams_table = "nfl_teams" if league_type.lower() == "nfl" else "cfb_teams"
        
        # Query database
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            
            # Try exact match first
            cursor.execute(
                f"SELECT user_id, team_name FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?",
                (team_key.lower(), server_id)
            )
            result = cursor.fetchone()
            
            # If no exact match, try partial match
            if not result:
                cursor.execute(
                    f"SELECT user_id, team_name FROM {teams_table} WHERE LOWER(team_name) LIKE ? AND server_id = ?",
                    (f"%{team_key.lower()}%", server_id)
                )
                result = cursor.fetchone()
        
        if not result:
            # Team not found in database
            pretty_team = format_team_name(team_name)
            return f"**{pretty_team}** is not in the database. Make sure the team name is correct."
        
        user_id, db_team_name = result
        pretty_team = format_team_name(db_team_name)
        
        if user_id is None:
            # Team is CPU
            return f"**{pretty_team}** is not assigned to anyone (CPU)."
        
        # Team is assigned to a user
        user_id = int(user_id)
        member = guild.get_member(user_id)
        
        if member:
            # Use display name with trophies
            display_name = member.display_name
            return f"**{pretty_team}** is assigned to {member.mention} ({display_name})."
        else:
            # User not in server anymore
            return f"**{pretty_team}** is assigned to <@{user_id}>."
            
    except Exception as e:
        print(f"[Pattern Match] Team ownership query error: {e}")
        import traceback
        traceback.print_exc()
        return f"⚠️ Error checking team ownership. Please try `/teams who-has team:{team_name}`"


def get_pattern_confidence(query: str) -> float:
    """
    Calculate confidence that we can handle this query with pattern matching
    
    Returns:
        Float 0.0-1.0 where:
        - 1.0 = 100% confident we can handle this
        - 0.0 = No confidence, use AI instead
    """
    normalized = normalize_query(query).lower()
    
    # High confidence patterns
    if is_team_ownership_query(query):
        _, team_name = extract_team_name(query)
        if team_name and len(team_name) > 2:
            return 0.95  # Very confident
    
    # Medium confidence patterns
    simple_patterns = [
        r'^help$',
        r'^commands?$',
        r'^what can you do$',
    ]
    
    import re
    for pattern in simple_patterns:
        if re.match(pattern, normalized):
            return 0.80
    
    # Low confidence
    return 0.0




