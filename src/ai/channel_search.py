"""
Cross-Channel Search Functionality
Searches across multiple Discord channels for historical information
"""

import discord
from typing import List, Dict, Optional
from .query_analyzer import extract_keywords
from .context_retriever import can_user_see_channel
from .message_history import get_full_message_content


def filter_relevant_channels(channels: List[discord.TextChannel], query: str) -> List[discord.TextChannel]:
    """
    Filter channels that might contain relevant information
    
    Args:
        channels: List of text channels
        query: Search query
        
    Returns:
        Filtered list of relevant channels
    """
    query_lower = query.lower()
    relevant = []
    
    # Keywords that suggest specific channel types
    if any(word in query_lower for word in ["advance", "next advance", "advance time"]):
        # Look for general channels, announcements, or league channels
        # Advance info is often in general/announcement channels
        for channel in channels:
            if any(word in channel.name.lower() for word in 
                   ["general", "announcements", "league", "info", "updates", "news"]):
                relevant.append(channel)
        # Also include all channels if no specific ones found (advance could be anywhere)
        if not relevant:
            relevant = channels
    
    elif any(word in query_lower for word in ["natty", "championship", "champ", "final"]):
        # Look for championship-related channels
        for channel in channels:
            if any(word in channel.name.lower() for word in 
                   ["champ", "natty", "final", "playoff", "bowl", "championship"]):
                relevant.append(channel)
    
    elif any(word in query_lower for word in ["week", "matchup", "game"]):
        # Look for matchup channels
        for channel in channels:
            if "-vs-" in channel.name or "week" in channel.name.lower():
                relevant.append(channel)
    
    elif any(word in query_lower for word in ["upgrade", "points", "attribute"]):
        # Look for attribute/points channels
        for channel in channels:
            if any(word in channel.name.lower() for word in 
                   ["attribute", "points", "upgrade", "ability"]):
                relevant.append(channel)
    
    # If no specific channels found, return all accessible channels
    return relevant if relevant else channels


def calculate_relevance(message_content: str, keywords: List[str], query: str) -> float:
    """
    Calculate relevance score for a message
    
    Args:
        message_content: Message content
        keywords: Extracted keywords from query
        query: Original query
        
    Returns:
        Relevance score (0.0 to 1.0)
    """
    if not message_content:
        return 0.0
    
    content_lower = message_content.lower()
    query_lower = query.lower()
    
    # Special handling for advance queries
    if "advance" in query_lower:
        # Boost score significantly if message contains advance-related terms
        advance_terms = ["advance", "next advance", "advance time", "league advanced"]
        if any(term in content_lower for term in advance_terms):
            score = 0.7  # High base score for advance-related messages
            # Boost if it has time/date information
            if any(word in content_lower for word in ["sunday", "monday", "tuesday", "wednesday", 
                                                      "thursday", "friday", "saturday", "pm", "am", ":"]):
                score = min(score + 0.2, 1.0)
            return score
    
    if not keywords:
        return 0.0
    
    # Count keyword matches
    keyword_matches = sum(1 for keyword in keywords if keyword in content_lower)
    
    # Base score from keyword matches
    score = min(keyword_matches / len(keywords), 1.0) if keywords else 0.0
    
    # Boost score if exact phrase appears
    if query_lower in content_lower:
        score = min(score + 0.3, 1.0)
    
    # Boost score if multiple keywords appear close together
    if keyword_matches >= 2:
        score = min(score + 0.2, 1.0)
    
    return score


async def search_channel_messages(
    channel: discord.TextChannel,
    query: str,
    limit: int = 10,
    max_history: int = 500
) -> List[Dict]:
    """
    Search a channel's message history for relevant content
    
    Args:
        channel: Discord text channel to search
        query: Search query
        limit: Maximum number of results
        max_history: Maximum messages to search through
        
    Returns:
        List of relevant messages with relevance scores
    """
    keywords = extract_keywords(query)
    relevant_messages = []
    
    # Lower threshold for recency-prioritized queries (they're important)
    query_lower = query.lower()
    recency_keywords = [
        "advance", "current", "now", "today", "this week", "latest", 
        "most recent", "active", "happening", "when is", "what's"
    ]
    should_prioritize_recency = any(keyword in query_lower for keyword in recency_keywords)
    threshold = 0.2 if should_prioritize_recency else 0.3
    
    try:
        async for message in channel.history(limit=max_history):
            # For recency-prioritized queries, include bot messages (they often contain important announcements)
            if message.author.bot and not should_prioritize_recency:
                continue
            
            # Get full message content including embeds
            full_content = get_full_message_content(message)
            
            # Skip if no content at all
            if not full_content.strip():
                continue
            
            # Check if message is relevant (using full content including embeds)
            relevance_score = calculate_relevance(full_content, keywords, query)
            
            if relevance_score > threshold:
                relevant_messages.append({
                    'content': full_content,  # Include embed content
                    'author': message.author.display_name,
                    'timestamp': message.created_at,
                    'relevance': relevance_score,
                    'channel': channel.name
                })
            
            if len(relevant_messages) >= limit:
                break
    except Exception as e:
        print(f"[Channel Search] Error searching channel {channel.name}: {e}")
    
    # Determine if query should prioritize recency
    # Queries about current/active information should prioritize recency
    recency_keywords = [
        "advance", "current", "now", "today", "this week", "latest", 
        "most recent", "active", "happening", "when is", "what's"
    ]
    
    should_prioritize_recency = any(keyword in query_lower for keyword in recency_keywords)
    
    # For queries about current state, prioritize recency (most recent first)
    # For historical queries, prioritize relevance but use recency as tiebreaker
    if should_prioritize_recency:
        # Sort by timestamp (most recent first), then by relevance as tiebreaker
        relevant_messages.sort(key=lambda x: (x['timestamp'], x['relevance']), reverse=True)
    else:
        # Sort by relevance (highest first), then by recency as tiebreaker
        # This ensures we get the most relevant answer, but if two are equally relevant, use the most recent
        relevant_messages.sort(key=lambda x: (x['relevance'], x['timestamp']), reverse=True)
    
    return relevant_messages


async def search_channels_for_answer(
    guild: discord.Guild,
    member: discord.Member,
    query: str,
    max_channels: int = 10
) -> List[Dict]:
    """
    Search across multiple channels for answers
    
    Args:
        guild: Discord guild
        member: Discord member (for permission checking)
        query: Search query
        max_channels: Maximum number of channels to search
        
    Returns:
        List of search results grouped by channel
    """
    # Get all channels user can view
    accessible_channels = [
        channel for channel in guild.text_channels
        if isinstance(channel, discord.TextChannel) and
           can_user_see_channel(channel, member) and
           channel.permissions_for(member).read_message_history
    ]
    
    # Filter to relevant channels
    relevant_channels = filter_relevant_channels(accessible_channels, query)
    
    # Limit number of channels to search
    channels_to_search = relevant_channels[:max_channels]
    
    # Search each channel
    results = []
    for channel in channels_to_search:
        messages = await search_channel_messages(channel, query, limit=5)
        if messages:
            results.append({
                'channel': channel.name,
                'channel_id': channel.id,
                'messages': messages
            })
    
    return results

