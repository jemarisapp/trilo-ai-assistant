"""
Message History Management
Handles retrieving and formatting message history for conversation context
"""

import discord
from typing import List, Dict, Optional
from datetime import datetime, timedelta


def extract_embed_content(message: discord.Message) -> str:
    """
    Extract text content from message embeds
    
    Args:
        message: Discord message
        
    Returns:
        Combined text from all embeds
    """
    embed_texts = []
    
    for embed in message.embeds:
        parts = []
        
        if embed.title:
            parts.append(embed.title)
        
        if embed.description:
            parts.append(embed.description)
        
        # Extract field content
        for field in embed.fields:
            if field.name:
                parts.append(f"{field.name}: {field.value}" if field.value else field.name)
            elif field.value:
                parts.append(field.value)
        
        if embed.footer and embed.footer.text:
            parts.append(embed.footer.text)
        
        if parts:
            embed_texts.append(" | ".join(parts))
    
    return " | ".join(embed_texts) if embed_texts else ""


def get_full_message_content(message: discord.Message) -> str:
    """
    Get full message content including embed text
    
    Args:
        message: Discord message
        
    Returns:
        Combined content from message text and embeds
    """
    content_parts = []
    
    # Add message content if it exists
    if message.content:
        content_parts.append(message.content)
    
    # Add embed content
    embed_content = extract_embed_content(message)
    if embed_content:
        content_parts.append(embed_content)
    
    return " | ".join(content_parts) if content_parts else ""


def should_include_message(message: discord.Message) -> bool:
    """
    Filter messages to include in context
    
    Args:
        message: Discord message to check
        
    Returns:
        True if message should be included, False otherwise
    """
    # Skip command invocations (they're handled separately)
    if message.content.startswith('/'):
        return False
    
    # Skip very long messages (likely spam or code blocks)
    if len(message.content) > 500:
        return False
    
    # Skip messages with only mentions/emojis
    if len(message.content.strip()) < 3:
        return False
    
    return True


async def get_recent_messages(
    channel: discord.TextChannel,
    limit: int = 20,
    before_message: Optional[discord.Message] = None
) -> List[Dict]:
    """
    Get recent messages from a channel
    
    Args:
        channel: Discord text channel
        limit: Maximum number of messages to retrieve
        before_message: Message to start before (for pagination)
        
    Returns:
        List of message dictionaries
    """
    messages = []
    
    try:
        async for message in channel.history(limit=limit, before=before_message):
            # Skip bot messages unless they're important announcements
            if message.author.bot:
                # Could add logic here to include important bot messages
                continue
            
            # Get full content including embeds
            full_content = get_full_message_content(message)
            
            # Skip if no content at all (including embeds)
            if not full_content.strip():
                continue
            
            # Skip command invocations
            if message.content and message.content.startswith('/'):
                continue
            
            # Skip very long messages (likely spam or code blocks)
            if len(full_content) > 500:
                continue
            
            messages.append({
                'author': message.author.display_name,
                'content': full_content,  # Use full content including embeds
                'timestamp': message.created_at,
                'is_bot': message.author.bot,
                'message_id': message.id
            })
    except Exception as e:
        print(f"[Message History] Error retrieving messages: {e}")
    
    # Return in chronological order (oldest first)
    return list(reversed(messages))


async def get_messages_in_timeframe(
    channel: discord.TextChannel,
    hours: float = 1.0,
    before_message: Optional[discord.Message] = None
) -> List[Dict]:
    """
    Get messages from the last N hours
    
    Args:
        channel: Discord text channel
        hours: Number of hours to look back
        before_message: Message to start before
        
    Returns:
        List of message dictionaries
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    messages = []
    
    try:
        async for message in channel.history(limit=100, before=before_message):
            if message.created_at < cutoff_time:
                break
            
            if message.author.bot:
                continue
            
            # Get full content including embeds
            full_content = get_full_message_content(message)
            
            # Skip if no content at all (including embeds)
            if not full_content.strip():
                continue
            
            # Skip command invocations
            if message.content and message.content.startswith('/'):
                continue
            
            # Skip very long messages
            if len(full_content) > 500:
                continue
            
            messages.append({
                'author': message.author.display_name,
                'content': full_content,  # Use full content including embeds
                'timestamp': message.created_at,
                'is_bot': message.author.bot,
                'message_id': message.id
            })
    except Exception as e:
        print(f"[Message History] Error retrieving messages by timeframe: {e}")
    
    return list(reversed(messages))


def build_conversation_context(messages: List[Dict], max_tokens: int = 2000) -> str:
    """
    Build conversation context from message history
    
    Args:
        messages: List of message dictionaries
        max_tokens: Maximum tokens to use (rough estimate: 1 token ≈ 4 chars)
        
    Returns:
        Formatted conversation context string
    """
    context_parts = []
    token_count = 0
    
    # Start from oldest and work forward
    for msg in messages:
        # Estimate tokens (rough: 1 token ≈ 4 characters, +10 for formatting)
        msg_tokens = len(msg['content']) // 4 + 10
        
        if token_count + msg_tokens > max_tokens:
            break
        
        # Format: "User: message"
        author = "Trilo" if msg['is_bot'] else msg['author']
        context_parts.append(f"{author}: {msg['content']}")
        token_count += msg_tokens
    
    return "\n".join(context_parts)


def parse_timeframe(text: str) -> Optional[float]:
    """
    Parse timeframe from natural language text
    
    Args:
        text: Text containing timeframe (e.g., "last 30 minutes", "past hour")
        
    Returns:
        Hours as float, or None if not found
    """
    text_lower = text.lower()
    
    # Extract numbers
    import re
    numbers = re.findall(r'\d+', text)
    number = float(numbers[0]) if numbers else 1.0
    
    # Determine unit
    if "minute" in text_lower:
        return number / 60.0
    elif "hour" in text_lower:
        return number
    elif "day" in text_lower:
        return number * 24.0
    elif "week" in text_lower:
        return number * 24.0 * 7.0
    
    return None

