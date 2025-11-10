"""
Context Retrieval System
Retrieves user, league, and matchup context from databases and Discord
"""

import discord
from typing import Dict, List, Optional, Tuple
from utils.utils import get_db_connection, clean_team_key, format_team_name
from commands.settings import get_server_setting, is_record_tracking_enabled


def can_user_see_channel(channel: discord.TextChannel, member: discord.Member) -> bool:
    """
    Check if a user can view a channel
    
    Args:
        channel: Discord text channel
        member: Discord member to check permissions for
        
    Returns:
        True if user can view the channel, False otherwise
    """
    try:
        return channel.permissions_for(member).view_channel
    except Exception:
        return False


def get_user_context(user_id: int, server_id: str) -> Dict:
    """
    Get comprehensive context about a user
    
    Args:
        user_id: Discord user ID
        server_id: Discord server ID
        
    Returns:
        Dictionary with user's team, record, points, and requests
    """
    context = {
        'team': None,
        'record': {'wins': 0, 'losses': 0},
        'points': 0,
        'pending_requests': [],
        'league_type': None
    }
    
    # Get league type
    league_type = get_server_setting(server_id, "league_type") or "cfb"
    context['league_type'] = league_type.lower()
    
    # Determine table names based on league type
    teams_table = f"{league_type}_teams" if league_type == "nfl" else "cfb_teams"
    records_table = f"{league_type}_team_records" if league_type == "nfl" else "cfb_team_records"
    
    # Get user's team
    try:
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT team_name FROM {teams_table} WHERE user_id = ? AND server_id = ?",
                (str(user_id), server_id)
            )
            team_row = cursor.fetchone()
            
            if team_row:
                context['team'] = team_row[0]
                
                # Get user's record
                if is_record_tracking_enabled(server_id):
                    cursor.execute(
                        f"SELECT wins, losses FROM {records_table} WHERE server_id = ? AND team_name = ?",
                        (server_id, team_row[0])
                    )
                    record_row = cursor.fetchone()
                    if record_row:
                        context['record'] = {
                            'wins': record_row[0],
                            'losses': record_row[1]
                        }
    except Exception as e:
        print(f"[Context Retrieval] Error getting user team: {e}")
    
    # Get user's attribute points (server-specific)
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            # Try the actual schema first (with server_id and 'available' column)
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (str(user_id), server_id)
            )
            points_row = cursor.fetchone()
            if points_row:
                context['points'] = points_row[0]
            else:
                # Fallback: try old schema (without server_id, with 'points' column)
                cursor.execute(
                    "SELECT points FROM attribute_points WHERE user_id = ?",
                    (str(user_id),)
                )
                points_row = cursor.fetchone()
                if points_row:
                    context['points'] = points_row[0]
            
            # Get pending requests (check both schemas)
            # Try with server_id first
            cursor.execute(
                """SELECT attribute_name, current_value, requested_value, points_cost, status
                   FROM attribute_requests
                   WHERE user_id = ? AND server_id = ? AND status = 'pending'
                   ORDER BY request_date DESC
                   LIMIT 5""",
                (str(user_id), server_id)
            )
            requests = cursor.fetchall()
            
            # If no results, try without server_id (old schema)
            if not requests:
                cursor.execute(
                    """SELECT attribute_name, current_value, requested_value, points_cost, status
                       FROM attribute_requests
                       WHERE user_id = ? AND status = 'pending'
                       ORDER BY request_date DESC
                       LIMIT 5""",
                    (str(user_id),)
                )
                requests = cursor.fetchall()
            
            context['pending_requests'] = [
                {
                    'attribute': req[0],
                    'current': req[1],
                    'requested': req[2],
                    'cost': req[3],
                    'status': req[4]
                }
                for req in requests
            ]
    except Exception as e:
        print(f"[Context Retrieval] Error getting user points: {e}")
    
    return context


def get_league_context(server_id: str) -> Dict:
    """
    Get league-wide context (standings, settings)
    
    Args:
        server_id: Discord server ID
        
    Returns:
        Dictionary with league standings and settings
    """
    context = {
        'league_type': None,
        'record_tracking_enabled': False,
        'standings': [],
        'total_teams': 0
    }
    
    # Get league type
    league_type = get_server_setting(server_id, "league_type") or "cfb"
    context['league_type'] = league_type.lower()
    context['record_tracking_enabled'] = is_record_tracking_enabled(server_id)
    
    # Determine table names
    teams_table = f"{league_type}_teams" if league_type == "nfl" else "cfb_teams"
    records_table = f"{league_type}_team_records" if league_type == "nfl" else "cfb_team_records"
    
    # Get standings
    try:
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            
            if context['record_tracking_enabled']:
                # Get standings with records
                cursor.execute(
                    f"""SELECT t.team_name, COALESCE(r.wins, 0) as wins, COALESCE(r.losses, 0) as losses
                        FROM {teams_table} t
                        LEFT JOIN {records_table} r ON t.team_name = r.team_name AND t.server_id = r.server_id
                        WHERE t.server_id = ?
                        ORDER BY COALESCE(r.wins, 0) DESC, COALESCE(r.losses, 0) ASC""",
                    (server_id,)
                )
            else:
                # Just get teams
                cursor.execute(
                    f"SELECT team_name FROM {teams_table} WHERE server_id = ?",
                    (server_id,)
                )
            
            standings = cursor.fetchall()
            context['standings'] = [
                {
                    'team': row[0],
                    'wins': row[1] if context['record_tracking_enabled'] else 0,
                    'losses': row[2] if context['record_tracking_enabled'] else 0
                }
                for row in standings
            ]
            context['total_teams'] = len(standings)
    except Exception as e:
        print(f"[Context Retrieval] Error getting league context: {e}")
    
    return context


def get_user_matchups(guild: discord.Guild, member: discord.Member, server_id: str) -> List[Dict]:
    """
    Get matchups involving a user's team from Discord channels
    Only returns channels the user can access
    
    Args:
        guild: Discord guild
        member: Discord member
        server_id: Discord server ID
        
    Returns:
        List of matchup dictionaries
    """
    matchups = []
    
    # Get user's team
    user_context = get_user_context(member.id, server_id)
    user_team = user_context.get('team')
    
    if not user_team:
        return matchups
    
    # Normalize team name for matching
    user_team_key = clean_team_key(user_team)
    
    # Find matchup categories
    matchup_categories = [
        cat for cat in guild.categories
        if cat and any(keyword in cat.name.lower() for keyword in 
                      ["week", "playoff", "bowl", "championship", "matchup"])
    ]
    
    # Status suffixes to check for
    status_suffixes = {"✅", "🎲", "☑️", "❎", "❌"}
    
    # Search through categories and channels
    for category in matchup_categories:
        # Check if user can see the category
        if not can_user_see_channel(category, member):
            continue
        
        for channel in category.channels:
            # Check if user can see this channel
            if not isinstance(channel, discord.TextChannel):
                continue
            
            if not can_user_see_channel(channel, member):
                continue
            
            # Check if it's a matchup channel
            channel_name = channel.name
            
            # Remove status suffixes
            for suffix in status_suffixes:
                if channel_name.endswith(f"-{suffix}"):
                    channel_name = channel_name[:-(len(suffix) + 1)]
                    break
            
            if "-vs-" not in channel_name:
                continue
            
            # Parse matchup
            try:
                team1_raw, team2_raw = channel_name.split("-vs-", 1)
                team1_key = clean_team_key(team1_raw)
                team2_key = clean_team_key(team2_raw)
                
                # Check if user's team is in this matchup
                if user_team_key.lower() in [team1_key.lower(), team2_key.lower()]:
                    # Determine opponent
                    opponent_key = team2_key if team1_key.lower() == user_team_key.lower() else team1_key
                    opponent_name = format_team_name(opponent_key)
                    
                    # Check game status from channel name
                    status = None
                    original_name = channel.name
                    for suffix in status_suffixes:
                        if original_name.endswith(f"-{suffix}"):
                            status = suffix
                            break
                    
                    matchups.append({
                        'category': category.name,
                        'channel': channel.name,
                        'opponent': opponent_name,
                        'opponent_key': opponent_key,
                        'status': status,
                        'channel_id': channel.id
                    })
            except Exception as e:
                print(f"[Context Retrieval] Error parsing matchup channel {channel.name}: {e}")
                continue
    
    return matchups

