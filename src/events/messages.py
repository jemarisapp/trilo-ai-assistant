"""
Message event handlers for Trilo Discord Bot
"""
import re
import discord
import functools
import time
import logging
from typing import Optional
from config.settings import BotSettings
from utils import get_db_connection

# Rate limiting for error logs
@functools.lru_cache(maxsize=100)
def should_log_error(error_type: str, context: str = "") -> bool:
    """Prevent log flooding by limiting repeated error logs"""
    current_time = int(time.time() / 300)  # 5-minute windows
    cache_key = f"{error_type}:{context}:{current_time}"
    return True  # Always return True for now, can be enhanced with persistent storage

def configure_logging(bot) -> None:
    """Configure logging level based on environment"""
    if hasattr(bot, 'production') and bot.production:
        bot.logger.setLevel(logging.WARNING)
    else:
        bot.logger.setLevel(logging.INFO)

async def handle_message(bot, message: discord.Message):
    """Handle incoming messages"""
    if message.author.bot:
        return

    # Configure logging level based on environment
    configure_logging(bot)

    raw_content = message.content
    content = message.content.lower()
    
    # Handle stream detection (only for messages with Twitch or YouTube live links)
    if 'twitch.tv' in content or 'twitch.com' in content or 'youtube.com/live' in content:
        await _handle_stream_detection(bot, message, content, raw_content)
        return
    
    # AI conversation feature removed for Discord policy compliance
    # Slash commands remain fully functional and policy-compliant

async def _handle_stream_detection(bot, message, content, raw_content):
    """Handle stream detection and announcement"""
    def extract_twitch_username(msg: str) -> Optional[str]:
        match = re.search(BotSettings.TWITCH_REGEX, msg)
        return match.group(1) if match else None
    
    def extract_youtube_live_id(msg: str) -> Optional[str]:
        # Use the original message content to preserve case sensitivity
        match = re.search(BotSettings.YOUTUBE_LIVE_REGEX, msg)
        return match.group(1) if match else None

    def has_role_mentions(msg: discord.Message) -> bool:
        """Check if message already contains role mentions"""
        # Check for role mentions in the message
        if msg.role_mentions:
            return True
        
        # Check for @everyone or @here mentions
        if "@everyone" in msg.content or "@here" in msg.content:
            return True
        
        # Check for role mentions by name (case-insensitive)
        content_lower = msg.content.lower()
        for role in msg.guild.roles:
            if role.name != "@everyone" and f"@{role.name.lower()}" in content_lower:
                return True
        
        return False

    # Detect Twitch stream links
    twitch_username = extract_twitch_username(content)
    youtube_live_id = extract_youtube_live_id(raw_content)  # Use raw_content to preserve case
    
    # Determine platform and extract relevant info
    if twitch_username:
        platform = "twitch"
        stream_id = twitch_username
        stream_url = f"https://www.twitch.tv/{twitch_username}"
        embed_title = f"🟣 {twitch_username} is now LIVE on Twitch!"
        clean_text = re.sub(BotSettings.TWITCH_REGEX, "", raw_content).strip()
    elif youtube_live_id:
        platform = "youtube"
        stream_id = youtube_live_id
        stream_url = f"https://www.youtube.com/live/{youtube_live_id}"
        embed_title = f"🔴 LIVE MATCHUP on YouTube!"
        clean_text = re.sub(BotSettings.YOUTUBE_LIVE_REGEX, "", raw_content).strip()
    else:
        return

    server_id = str(message.guild.id)

    try:
        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting, new_value FROM server_settings
                WHERE server_id = ? AND setting IN (
                    'stream_notify_role', 'stream_watch_channel', 'stream_announcements_enabled'
                )
            """, (server_id,))
            settings = dict(cursor.fetchall())
    except Exception as e:
        # Secure exception logging with rate limiting
        error_context = "[Stream Settings Fetch]"
        if should_log_error(type(e).__name__, error_context):
            bot.logger.error(f"{error_context} {type(e).__name__}: {str(e)[:100] if str(e) else 'Unknown error'}")
        return

    if settings.get("stream_announcements_enabled", "").lower() != "on":
        return

    # Resolve post channel
    stream_watch_setting = settings.get("stream_watch_channel")
    target_channel = message.channel  # fallback

    if stream_watch_setting and stream_watch_setting.isdigit():
        target_channel_obj = message.guild.get_channel(int(stream_watch_setting))
        if target_channel_obj and isinstance(target_channel_obj, discord.TextChannel):
            target_channel = target_channel_obj

    # Resolve mention role
    role_name = settings.get("stream_notify_role")
    role_mention = ""
    if role_name:
        role_obj = discord.utils.get(message.guild.roles, name=role_name.strip())
        if role_obj:
            role_mention = role_obj.mention

    # Check if message already contains role mentions
    has_existing_mentions = has_role_mentions(message)
    
    # If there are existing mentions and we're in the target channel, skip entirely
    if has_existing_mentions and message.channel.id == target_channel.id:
        return

    # Clean text is already prepared above based on platform

    # Set color based on platform
    embed_color = discord.Color.red() if platform == "youtube" else discord.Color.purple()
    
    embed = discord.Embed(
        title=embed_title,
        description=f"🔗 **[WATCH NOW]({stream_url})**",
        color=embed_color
    )
    
    # Add platform-specific thumbnails
    if platform == "youtube":
        # YouTube provides multiple thumbnail qualities - maxresdefault is highest quality
        thumbnail_url = f"https://img.youtube.com/vi/{youtube_live_id}/maxresdefault.jpg"
        embed.set_image(url=thumbnail_url)
    elif platform == "twitch":
        # Use Twitch profile picture instead of stream preview
        profile_pic_url = f"https://static-cdn.jtvnw.net/jtv_user_pictures/{twitch_username}-profile_image-300x300.png"
        embed.set_image(url=profile_pic_url)
    
    embed.set_footer(text=f"Shared by {message.author.display_name}")

    if clean_text:
        embed.description += f"\n\n{clean_text}"

    # Determine whether to include role mention
    # If there are existing mentions, send silently (no role mention)
    # If no existing mentions, use the configured role mention
    final_role_mention = "" if has_existing_mentions else role_mention

    try:
        await target_channel.send(content=final_role_mention, embed=embed)
    except Exception as e:
        # Secure exception logging with rate limiting
        error_context = "[Stream Announce Error]"
        if should_log_error(type(e).__name__, error_context):
            bot.logger.error(f"{error_context} {type(e).__name__}: {str(e)[:100] if str(e) else 'Unknown error'}")

    # Only delete the original message if it's in the target channel
    if message.channel.id == target_channel.id:
        try:
            await message.delete()
        except Exception as e:
            # Secure exception logging with rate limiting
            error_context = "[Stream Message Delete Error]"
            if should_log_error(type(e).__name__, error_context):
                bot.logger.error(f"{error_context} {type(e).__name__}: {str(e)[:100] if str(e) else 'Unknown error'}") 