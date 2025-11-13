"""
Main Conversation Handler
Handles AI-powered conversations with users
"""

import os
import discord
from typing import Optional, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

from .prompts import SYSTEM_PROMPT, CONVERSATION_CONTEXT_TEMPLATE
from .context_retriever import get_user_context, get_league_context, get_user_matchups
from .message_history import get_recent_messages, get_messages_in_timeframe, build_conversation_context
from .query_analyzer import classify_query_type, detect_search_intent, detect_summary_intent
from .channel_search import search_channels_for_answer
from .command_bridge import detect_command_intent
from .agent import classify_query_intent, extract_command_topic
from .command_retriever import search_knowledge_base, format_command_help
from .command_executor import execute_command
from .setup_retriever import search_setup_guide, format_setup_help, get_quick_start_guide, get_full_commissioner_guide, get_player_guide, load_setup_guide
from .setup_agent import process_setup_question
from .token_tracker import get_tracker
from .query_normalizer import normalize_query
from .query_patterns import try_direct_pattern_match, get_pattern_confidence
from .query_cache import get_query_cache, should_cache_query

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("❌ No OpenAI API Key found. Make sure it's in secrets.env")

client = OpenAI(api_key=OPENAI_API_KEY)


def format_user_context(user_context: Dict, record_tracking_enabled: bool = False) -> str:
    """Format user context for AI prompt"""
    context_parts = []
    
    if user_context.get('team'):
        context_parts.append(f"Team: {user_context['team']}")
    
    # Only include record if record tracking is enabled
    if record_tracking_enabled and user_context.get('record'):
        rec = user_context['record']
        context_parts.append(f"Record: {rec['wins']}-{rec['losses']}")
    
    if user_context.get('points'):
        context_parts.append(f"Attribute Points: {user_context['points']}")
    
    if user_context.get('pending_requests'):
        context_parts.append(f"Pending Upgrade Requests: {len(user_context['pending_requests'])}")
    
    return "\n".join(context_parts) if context_parts else "No team assigned yet."


async def get_ai_response(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 500) -> str:
    """
    Get response from OpenAI API
    
    Args:
        prompt: Full prompt including system message and context
        model: Model to use (gpt-4o-mini for cost, gpt-4o for complex queries)
        max_tokens: Maximum tokens in response
        
    Returns:
        AI response text
    """
    try:
        import time
        start_time = time.time()
        tracker = get_tracker()
        
        # Estimate input tokens
        full_prompt = SYSTEM_PROMPT + "\n" + prompt
        input_tokens = tracker.estimate_tokens(full_prompt)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        
        # Log token usage
        output_tokens = tracker.estimate_tokens(result)
        duration_ms = (time.time() - start_time) * 1000
        tracker.log_usage("general_conversation", model, input_tokens, output_tokens, duration_ms)
        
        return result
    except Exception as e:
        print(f"[AI Conversation] Error getting AI response: {e}")
        return "Sorry, I'm having trouble processing that right now. Please try again!"


async def handle_ai_conversation(bot, message: discord.Message) -> Optional[discord.Message]:
    """
    Main handler for AI conversations
    
    Args:
        bot: Discord bot instance
        message: Discord message that triggered the conversation
        
    Returns:
        Sent message if successful, None otherwise
    """
    # Remove bot mention from message
    query = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    
    if not query:
        return None
    
    server_id = str(message.guild.id) if message.guild else None
    
    # ===================================================================
    # LAYER 1: Query Cache - Check if we've seen this exact query before
    # ===================================================================
    cache = get_query_cache()
    cached_response = cache.get(query, server_id)
    if cached_response:
        print(f"[AI Conversation] Using cached response for: '{query}'")
        return await message.channel.send(cached_response)
    
    # ===================================================================
    # LAYER 2: Pattern Matching - Try direct routing for common patterns
    # ===================================================================
    confidence = get_pattern_confidence(query)
    if confidence > 0.9:  # High confidence in pattern match
        print(f"[AI Conversation] Using pattern match for: '{query}' (confidence: {confidence})")
        handled, response = await try_direct_pattern_match(bot, message, query, server_id)
        if handled and response:
            # Cache the response
            if should_cache_query(query, response):
                cache.set(query, server_id, response)
            return await message.channel.send(response)
    
    # ===================================================================
    # LAYER 3: Query Normalization - Standardize query for AI processing
    # ===================================================================
    normalized_query = normalize_query(query)
    if normalized_query != query:
        print(f"[AI Conversation] Normalized: '{query}' → '{normalized_query}'")
    
    # Use agent to classify query intent
    query_intent = classify_query_intent(query)
    
    # Handle command execution requests (Phase 2)
    if query_intent == "command_execute":
        result = await execute_command(bot, message, query, server_id)
        if result:
            return await message.channel.send(result)
        # If result is None, it might mean the command handled its own response (e.g., sent a message with buttons)
        # Check if the command was for create-from-image (which returns None after sending preview)
        if message.attachments and any(phrase in query.lower() for phrase in [
            "create matchups", "create from image", "matchups from image", 
            "create from this", "extract matchups", "process image"
        ]):
            # Command already sent its own response (preview with buttons), don't send error
            return None
        # Check if the command was for delete categories (which returns None after sending preview)
        if any(phrase in query.lower() for phrase in [
            "delete matchups", "delete categories", "remove matchups", "remove categories",
            "delete category", "remove category", "clear matchups", "delete week", "remove week"
        ]):
            # Command already sent its own response (preview with buttons), don't send error
            return None
        # Check if the command was for tag users (which returns None after executing)
        if any(phrase in query.lower() for phrase in [
            "tag users", "tag players", "notify users", "mention users"
        ]):
            # Command already sent its own response, don't send error
            return None
        # Check if the command was for announce advance (which returns None after sending preview)
        if any(phrase in query.lower() for phrase in [
            "announce advance", "announce week", "advance announcement",
            "notify advance", "post advance", "send advance"
        ]):
            # Command already sent its own response (preview with buttons), don't send error
            return None
        # If execution failed, don't fall through - explicitly state failure
        # This prevents AI from simulating write commands
        return await message.channel.send(
            "⚠️ I couldn't execute that command. Please try using the slash command directly, "
            "or rephrase your request more clearly."
        )
    
    # Handle setup/getting started requests
    if query_intent == "setup_help":
        return await handle_setup_help(bot, message, query, server_id)
    
    # Handle command help requests with RAG
    if query_intent == "command_help":
        return await handle_command_help(bot, message, query, server_id)
    
    # Classify query type for other intents
    query_type = classify_query_type(query)
    
    # Handle different query types
    if query_type == "search":
        # Cross-channel search
        return await handle_search_query(bot, message, query, server_id)
    elif query_type == "matchups":
        # Matchup queries - read channels directly
        return await handle_matchups_query(bot, message, query, server_id)
    elif query_type == "summary":
        # Summary request (will be implemented in Phase 3)
        return await handle_summary_request(bot, message, query, server_id)
    else:
        # Regular conversation (handles user_specific, league_specific, and general)
        return await handle_regular_conversation(bot, message, query, server_id, query_intent)


async def handle_setup_help(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """Handle setup/getting started requests using agentic system"""
    
    # Load the full setup guide
    guide_text = load_setup_guide()
    
    if not guide_text:
        return await message.channel.send(
            "I couldn't load my setup guide. Try using /settings help or /help for command information."
        )
    
    # Use multi-agent system to process the question
    # This prevents hallucination by:
    # 1. Extracting intent (what they're asking about)
    # 2. Searching documentation (finding exact text)
    # 3. Extracting commands (only actual commands from docs)
    # 4. Synthesizing response (using only found information)
    response = process_setup_question(query, guide_text)
    
    # Discord has a 2000 character limit - split if needed
    if len(response) <= 2000:
        return await message.channel.send(response)
    else:
        # Split into chunks at logical points (paragraphs, sentences)
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = response.split('\n\n')
        
        for para in paragraphs:
            # If adding this paragraph would exceed limit, send current chunk
            if len(current_chunk) + len(para) + 2 > 1900:  # Leave buffer
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Send chunks sequentially
        sent_message = None
        for chunk in chunks:
            sent_message = await message.channel.send(chunk)
        
        return sent_message


async def handle_setup_help_old(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """OLD VERSION - Handle setup/getting started requests"""
    
    # Check if they want a specific guide based on query content
    query_lower = query.lower()
    
    # Detect query focus from keywords
    is_commissioner_query = any(phrase in query_lower for phrase in [
        "commissioner", "admin", "set up league", "setup league", "manage", 
        "configure", "create matchups", "give points", "set up my league"
    ])
    
    is_player_query = any(phrase in query_lower for phrase in [
        "player", "member", "user", "my team", "my points", "how do i play"
    ])
    
    if any(phrase in query_lower for phrase in ["quick start", "checklist"]):
        # Return quick start guide
        guide_content = get_quick_start_guide()
        focus = "quick_start"
    elif is_commissioner_query:
        # Return full commissioner guide
        guide_content = get_full_commissioner_guide()
        focus = "commissioner"
    elif is_player_query:
        # Return player guide
        guide_content = get_player_guide()
        focus = "player"
    else:
        # General "how to use" queries - search for relevant sections
        sections = search_setup_guide(query)
        
        if not sections:
            # Default to comprehensive overview (first-time users section)
            guide_content = get_quick_start_guide()
            focus = "overview"
        else:
            # Format the found sections
            guide_content = format_setup_help(sections)
            focus = "specific"
    
    # Build AI prompt based on focus
    if focus == "overview":
        prompt = f"""The user is asking for general help using Trilo: "{query}"

Here is the setup guide overview:
{guide_content}

Provide a clear, helpful introduction to Trilo. Explain:
1. What Trilo does (sports league management bot)
2. Who uses it (commissioners manage leagues, players participate)
3. Key features at a high level
4. How to get started (mention they can ask more specific questions)

Keep it conversational and direct - no excessive enthusiasm. Be welcoming to both commissioners and players.

CRITICAL: Only provide information from the setup guide. If something isn't covered in the guide, say "I don't have specific information about that in my setup guide. Try using /settings help or ask me about a specific feature."

IMPORTANT: Keep your response under 1500 characters. Be concise but helpful."""

    elif focus == "commissioner":
        prompt = f"""The user is asking about setting up or managing a league with Trilo: "{query}"

Here is the commissioner setup guide:
{guide_content}

Provide a clear, helpful response for commissioners/admins. Focus on:
- Setup steps and configuration
- League management features
- How to use admin commands
- Best practices for running a league

Keep it conversational and direct - no excessive enthusiasm. Assume they may not have roles set up yet.

CRITICAL: Only use information from the provided guide. Do NOT invent commands or features that aren't mentioned. If something isn't in the guide, say "I don't have information about that specific feature. Try /settings help or /help for command options."

IMPORTANT: Keep your response under 1500 characters. Be concise but helpful."""

    elif focus == "player":
        prompt = f"""The user is asking how to use Trilo as a player/member: "{query}"

Here is the player usage guide:
{guide_content}

Provide a clear, helpful response for league members. Focus on:
- How to check their team and points
- How to use basic commands
- How to interact with the bot naturally
- What they can do as a participant

Keep it conversational and direct - no excessive enthusiasm.

CRITICAL: Only use information from the provided guide. Do NOT make up commands or features. If something isn't documented, say "I don't have information about that. Ask your commissioner or try /help."

IMPORTANT: Keep your response under 1500 characters. Be concise but helpful."""

    elif focus == "quick_start":
        prompt = f"""The user is asking for a quick start guide: "{query}"

Here is the quick start information:
{guide_content}

Provide a concise, actionable quick start guide. Focus on:
- Essential first steps
- What needs to be configured
- How to get up and running quickly

Keep it conversational and direct - no excessive enthusiasm. Be efficient and to the point.

CRITICAL: Only use information from the provided guide. Do NOT invent steps or commands not mentioned in the guide.

IMPORTANT: Keep your response under 1500 characters. Be concise but helpful."""

    else:
        # Specific topic
        prompt = f"""The user is asking for help with Trilo: "{query}"

Here is the relevant information from the setup guide:
{guide_content}

Provide a clear, helpful response based on this information. Keep it conversational and direct - no excessive enthusiasm. 

Tailor your response to their specific question, covering both commissioner and player perspectives if relevant.

CRITICAL - READ CAREFULLY:
1. ONLY use commands and information explicitly shown in the provided guide text
2. If you see "/settings set setting:stream_announcements_enabled" in the guide, use THAT EXACT command
3. Do NOT create fake commands like "/stream-notis" or "/stream setup"
4. Do NOT invent command syntax that isn't explicitly documented
5. If the guide shows specific `/settings` commands for streams, USE THOSE
6. If something isn't clearly documented in the provided text, say: "I don't have detailed information about that. Try /settings help or /help."

DO NOT HALLUCINATE COMMANDS. USE ONLY WHAT'S DOCUMENTED.

IMPORTANT: Keep your response under 1500 characters. Be concise but helpful."""

    # Use gpt-4o for setup help - better instruction following, less hallucination
    response = await get_ai_response(prompt, model="gpt-4o", max_tokens=600)
    
    # Discord has a 2000 character limit - split if needed
    if len(response) <= 2000:
        return await message.channel.send(response)
    else:
        # Split into chunks at logical points (paragraphs, sentences)
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = response.split('\n\n')
        
        for para in paragraphs:
            # If adding this paragraph would exceed limit, send current chunk
            if len(current_chunk) + len(para) + 2 > 1900:  # Leave buffer
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Send chunks sequentially
        sent_message = None
        for chunk in chunks:
            sent_message = await message.channel.send(chunk)
        
        return sent_message


async def handle_command_help(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """Handle command help requests using RAG from knowledge base"""
    
    # Extract command topic
    topic = extract_command_topic(query)
    
    # Search knowledge base
    command_info = search_knowledge_base(query, topic)
    
    # Format help information
    formatted_help = format_command_help(command_info, query)
    
    # Use AI to synthesize a helpful response based on the command documentation
    prompt = f"""The user is asking for help with a command: "{query}"

Here is the relevant command documentation:
{formatted_help}

Provide a clear, concise answer explaining how to use the command. Keep it straightforward and casual. 
If the documentation shows a specific command (like `/attributes request`), explain:
1. What the command does
2. How to use it (the command syntax)
3. What parameters are needed
4. A brief example if helpful

Keep it conversational and easy to understand. Be direct - no need for excessive enthusiasm."""

    response = await get_ai_response(prompt, model="gpt-4o-mini", max_tokens=400)
    
    return await message.channel.send(response)


async def handle_regular_conversation(
    bot,
    message: discord.Message,
    query: str,
    server_id: str,
    query_intent: str = "general"
) -> Optional[discord.Message]:
    """Handle regular conversational queries"""

    # Get conversation history
    recent_messages = await get_recent_messages(message.channel, limit=15, before_message=message)
    conversation_history = build_conversation_context(recent_messages, max_tokens=1500)

    # Get league context first to check record tracking
    league_context = get_league_context(server_id) if server_id else {}
    record_tracking_enabled = league_context.get('record_tracking_enabled', False)

    # Get user context - ALWAYS use the message author, never the bot
    user_context = get_user_context(message.author.id, server_id) if server_id else {}
    user_context_str = format_user_context(user_context, record_tracking_enabled=record_tracking_enabled)
    
    # Detect if this is a prediction/winner question
    query_lower = query.lower()
    is_prediction_query = any(phrase in query_lower for phrase in [
        "who will win", "who's going to win", "who wins", "pick a winner",
        "who do you think", "predict", "prediction"
    ])
    
    # Build prompt
    if is_prediction_query:
        # For prediction queries, be casual and laid-back, don't mention unrelated context
        prompt = f"""The user is asking a casual prediction question: "{query}"

{CONVERSATION_CONTEXT_TEMPLATE.format(
    conversation_history=conversation_history,
    user_message=query
)}

Respond in a casual, chill way. You don't have access to real stats or historical data, so just make a straightforward prediction and pick a winner. Be natural and conversational. Don't mention attribute points, records, or other unrelated features unless the user specifically asks about them.

Vary your response style! Use different approaches:
- Direct: "I'm taking [Team] in this one."
- Confident: "[Team] all day. This is their game to lose."
- Casual: "Gotta go with [Team] here."
- Low-key: "[Team] should take it."
- Simple: "[Team] has the edge in this matchup."
- Relaxed: "I'm rolling with [Team] on this one."
- Short: "[Team] takes it."
- Matter-of-fact: "This one's going to [Team]."

Mix it up - don't use the same phrases. Be natural and varied. Keep it chill - no excessive emojis or enthusiasm."""
    else:
        # For regular queries, include context but only mention it if relevant
        prompt = f"""You are responding to a message from a USER named {message.author.display_name} (not yourself).

User Context for {message.author.display_name} (only mention if directly relevant to the query):
{user_context_str}

League Type: {league_context.get('league_type', 'CFB')}
Record Tracking: {'Enabled' if record_tracking_enabled else 'Disabled'}

{CONVERSATION_CONTEXT_TEMPLATE.format(
    conversation_history=conversation_history,
    user_message=query
)}

CRITICAL: You are Trilo, a bot. The user is {message.author.display_name}. When talking about attribute points, records, or team assignments, you are talking about THE USER'S data, not your own. You (Trilo) do not have attribute points or a team.

Respond naturally and directly. Only mention user context (like attribute points, team assignments, records) if it's directly relevant to what the user is asking about.

CRITICAL RULES:
- DO NOT mention attribute points, records, or team assignments unless the user is specifically asking about them
- If the user asks "how many points do I have?" - then mention THE USER'S points, not yours
- If the user asks "who will win?" - do NOT mention points or other unrelated info
- Record Tracking only affects WIN/LOSS RECORDS. If disabled, don't mention win/loss records.
- Be casual and conversational, stay on topic
- Keep emojis to a minimum - only use when truly helpful
- NEVER say "Trilo has X points" - always refer to the user's data"""

    # Get AI response
    response = await get_ai_response(prompt, model="gpt-4o-mini")
    
    # Send response
    return await message.channel.send(response)


async def handle_search_query(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """Handle cross-channel search queries"""
    
    if not message.guild:
        return await message.channel.send("Search is only available in servers, not DMs.")
    
    # Search channels
    search_results = await search_channels_for_answer(
        message.guild,
        message.author,
        query,
        max_channels=10
    )
    
    if not search_results:
        return await message.channel.send(
            f"I couldn't find any relevant information about \"{query}\" in the channels you have access to."
        )
    
    # Build context from search results
    from .prompts import SEARCH_SYNTHESIS_PROMPT
    
    # Determine if query should prioritize recency
    query_lower = query.lower()
    recency_keywords = [
        "advance", "current", "now", "today", "this week", "latest", 
        "most recent", "active", "happening", "when is", "what's"
    ]
    should_prioritize_recency = any(keyword in query_lower for keyword in recency_keywords)
    
    context_parts = []
    for result in search_results[:5]:  # Limit to top 5 channels
        channel_name = result['channel']
        # For recency-prioritized queries, use fewer messages (most recent is already first)
        # For other queries, use top 3 messages
        message_limit = 1 if should_prioritize_recency else 3
        messages = result['messages'][:message_limit]
        
        context_parts.append(f"\n--- Messages from #{channel_name} ---")
        for msg in messages:
            # Include full timestamp for recency-prioritized queries to help AI identify most recent
            if should_prioritize_recency:
                timestamp = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = msg['timestamp'].strftime('%Y-%m-%d')
            context_parts.append(f"{msg['author']} ({timestamp}): {msg['content']}")
    
    search_context = "\n".join(context_parts)
    
    # Adjust prompt based on whether recency matters
    synthesis_prompt = SEARCH_SYNTHESIS_PROMPT
    if should_prioritize_recency:
        synthesis_prompt = f"""Based on the following messages from Discord channels, answer this question: "{{query}}"

Search Results (messages are listed with timestamps - use the MOST RECENT message for current/active information):
{{search_results}}

IMPORTANT: Use the MOST RECENT message for questions about current state. Check the timestamps - the message with the latest date/time contains the current/active information.

Provide a clear, concise answer using the most recent information. If multiple sources mention the same thing, that increases confidence.
Include the channel name if relevant."""
    else:
        # For historical queries, emphasize finding the definitive answer
        synthesis_prompt = f"""Based on the following messages from Discord channels, answer this question: "{{query}}"

Search Results:
{{search_results}}

Provide a clear, concise answer. For historical questions, look for definitive statements or announcements. If multiple sources mention the same thing, that increases confidence.
Include the channel name if relevant."""
    
    # Synthesize answer
    prompt = synthesis_prompt.format(
        query=query,
        search_results=search_context
    )
    
    answer = await get_ai_response(prompt, model="gpt-4o", max_tokens=300)
    
    # Create embed with answer
    embed = discord.Embed(
        description=answer,
        color=discord.Color.blue()
    )
    embed.set_footer(text="💡 Searched across accessible channels")
    
    return await message.channel.send(embed=embed)


async def handle_matchups_query(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """Handle matchup queries by reading channels directly from categories"""
    
    if not message.guild:
        return await message.channel.send("Matchup queries are only available in servers, not DMs.")
    
    from .context_retriever import can_user_see_channel
    from utils.utils import clean_team_key, format_team_name
    
    query_lower = query.lower()
    
    # Find matchup categories
    matchup_categories = [
        cat for cat in message.guild.categories
        if cat and any(keyword in cat.name.lower() for keyword in 
                      ["week", "playoff", "bowl", "championship", "matchup"])
    ]
    
    # Filter categories user can see
    accessible_categories = [
        cat for cat in matchup_categories
        if can_user_see_channel(cat, message.author)
    ]
    
    if not accessible_categories:
        return await message.channel.send(
            "I couldn't find any matchup categories you have access to."
        )
    
    # Determine which week/category to show
    import re
    
    # Check if query specifies a week
    week_match = re.search(r'week\s+(\d+)', query_lower)
    target_week = None
    if week_match:
        target_week = int(week_match.group(1))
    
    # Handle "this week" queries - find most recent week
    if "this week" in query_lower or "current week" in query_lower:
        week_numbers = []
        for cat in accessible_categories:
            cat_week_match = re.search(r'week\s+(\d+)', cat.name.lower())
            if cat_week_match:
                week_numbers.append((int(cat_week_match.group(1)), cat))
        
        if week_numbers:
            # Get the highest week number (most recent)
            max_week, max_cat = max(week_numbers, key=lambda x: x[0])
            accessible_categories = [max_cat]  # Only process the most recent week
    
    # Collect matchups from categories
    all_matchups = []
    status_suffixes = {"✅", "🎲", "☑️", "❎", "❌"}
    
    for category in accessible_categories:
        # If looking for specific week, filter by category name
        if target_week:
            category_week_match = re.search(r'week\s+(\d+)', category.name.lower())
            if category_week_match:
                if int(category_week_match.group(1)) != target_week:
                    continue
        
        for channel in category.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            
            if not can_user_see_channel(channel, message.author):
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
                
                team1_name = format_team_name(team1_key)
                team2_name = format_team_name(team2_key)
                
                all_matchups.append({
                    'category': category.name,
                    'team1': team1_name,
                    'team2': team2_name,
                    'channel': channel.name
                })
            except Exception:
                continue
    
    if not all_matchups:
        return await message.channel.send(
            f"I couldn't find any matchups in the categories you have access to."
        )
    
    # Group matchups by category
    categories_dict = {}
    for matchup in all_matchups:
        cat = matchup['category']
        if cat not in categories_dict:
            categories_dict[cat] = []
        categories_dict[cat].append(matchup)
    
    # Format response directly with actual team names - don't let AI hallucinate
    response_parts = []
    
    if target_week:
        response_parts.append(f"**Week {target_week} Matchups:**\n")
        # Add all matchups from all categories for this week
        for cat, matchups in categories_dict.items():
            for m in matchups:
                response_parts.append(f"• {m['team1']} vs {m['team2']}")
    elif "this week" in query_lower or "current week" in query_lower:
        # Find the category name for "this week"
        week_cat = list(categories_dict.keys())[0] if categories_dict else "This Week"
        response_parts.append(f"**{week_cat} Matchups:**\n")
        # Add matchups from the current week category
        for cat, matchups in categories_dict.items():
            for m in matchups:
                response_parts.append(f"• {m['team1']} vs {m['team2']}")
    else:
        # Group by category
        for cat, matchups in categories_dict.items():
            response_parts.append(f"**{cat}:**")
            for m in matchups:
                response_parts.append(f"• {m['team1']} vs {m['team2']}")
            response_parts.append("")
    
    # Build the final response with actual team names
    response_text = "\n".join(response_parts)
    
    # Add a casual closing
    response_text += "\n\nThere's your matchups for the week."
    
    return await message.channel.send(response_text)


async def handle_summary_request(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[discord.Message]:
    """Handle summary requests"""
    
    # Extract timeframe from query
    timeframe_info = extract_timeframe(query)
    timeframe_type = timeframe_info['type']
    timeframe_value = timeframe_info['value']
    
    # Get messages based on timeframe
    if timeframe_type == 'messages':
        # Get last N messages
        messages = await get_recent_messages(message.channel, limit=timeframe_value, before_message=message)
        timeframe_description = f"last {timeframe_value} messages"
    elif timeframe_type == 'hours':
        # Get messages from last N hours
        messages = await get_messages_in_timeframe(message.channel, hours=timeframe_value)
        timeframe_description = f"last {timeframe_value} hour{'s' if timeframe_value != 1 else ''}"
    elif timeframe_type == 'days':
        # Get messages from last N days
        messages = await get_messages_in_timeframe(message.channel, hours=timeframe_value * 24)
        timeframe_description = f"last {timeframe_value} day{'s' if timeframe_value != 1 else ''}"
    else:
        # Default: last 50 messages
        messages = await get_recent_messages(message.channel, limit=50, before_message=message)
        timeframe_description = "recent conversation"
    
    if not messages:
        return await message.channel.send(
            "There aren't any messages to summarize in this timeframe."
        )
    
    # Build conversation text for summarization
    conversation_lines = []
    for msg in reversed(messages):  # Show oldest first
        # Messages are dictionaries with 'timestamp', 'author', 'content' keys
        timestamp = msg['timestamp'].strftime("%I:%M %p")
        author = msg['author']
        content = msg['content']
        
        conversation_lines.append(f"[{timestamp}] {author}: {content}")
    
    conversation_text = "\n".join(conversation_lines)
    
    # Generate summary using AI
    from .prompts import SUMMARY_PROMPT_TEMPLATE
    
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        timeframe=timeframe_description,
        conversation_text=conversation_text
    )
    
    summary = await get_ai_response(prompt, model="gpt-4o-mini", max_tokens=500)
    
    # Format response
    response = f"**Summary ({timeframe_description}):**\n\n{summary}"
    
    return await message.channel.send(response)


def extract_timeframe(query: str) -> dict:
    """
    Extract timeframe information from summary query
    
    Args:
        query: User's query text
        
    Returns:
        Dictionary with 'type' and 'value' keys
    """
    import re
    query_lower = query.lower()
    
    # Check for specific number of messages
    message_patterns = [
        r'last (\d+) messages?',
        r'past (\d+) messages?',
        r'(\d+) messages?'
    ]
    
    for pattern in message_patterns:
        match = re.search(pattern, query_lower)
        if match:
            num_messages = int(match.group(1))
            return {'type': 'messages', 'value': min(num_messages, 100)}  # Cap at 100
    
    # Check for hours
    hour_patterns = [
        r'last (\d+) hours?',
        r'past (\d+) hours?'
    ]
    
    for pattern in hour_patterns:
        match = re.search(pattern, query_lower)
        if match:
            hours = int(match.group(1))
            return {'type': 'hours', 'value': min(hours, 72)}  # Cap at 3 days
    
    # Check for days
    day_patterns = [
        r'last (\d+) days?',
        r'past (\d+) days?',
        r'yesterday'
    ]
    
    for pattern in day_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if pattern == r'yesterday':
                days = 1
            else:
                days = int(match.group(1))
            return {'type': 'days', 'value': min(days, 7)}  # Cap at 1 week
    
    # Check for common phrases
    if 'today' in query_lower:
        return {'type': 'hours', 'value': 24}
    elif 'this week' in query_lower or 'week' in query_lower:
        return {'type': 'days', 'value': 7}
    
    # Default: last 50 messages
    return {'type': 'messages', 'value': 50}

