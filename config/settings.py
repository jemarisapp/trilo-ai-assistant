"""
Bot settings and environment configuration
"""
import os
from dotenv import load_dotenv
from pathlib import Path

class BotSettings:
    """Centralized bot settings and configuration"""
    
    # Load environment variables
    ENV_PATH = Path(__file__).parent.parent / "secrets.env"
    load_dotenv(dotenv_path=ENV_PATH)
    
    # Environment selection
    ENV = (os.getenv("ENV") or "dev").lower()

    # Bot tokens and API keys (selected by ENV)
    if ENV == "prod":
        DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    else:
        DISCORD_TOKEN = os.getenv("DEV_DISCORD_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Bot configuration
    COMMAND_PREFIX = "!"
    SUPPORT_SERVER_URL = "https://discord.gg/zRQzvJWnUt"
    
    # Valid reaction emojis
    VALID_REACTIONS = {"✅", "🎲", "🟥", "🟦", "🔴", "🔵"}
    
    # Commissioner role names
    COMMISSIONER_ROLES = {"Commish", "Commissioners", "Commissioner"}
    
    # Stream detection patterns
    TWITCH_REGEX = r"(?:https?://)?(?:www\.|m\.)?twitch\.tv/([a-zA-Z0-9_]+)"
    YOUTUBE_LIVE_REGEX = r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)(?:\?si=[a-zA-Z0-9_-]+)?"
    
    @classmethod
    def validate_environment(cls):
        """Validate that required environment variables are set"""
        if not cls.DISCORD_TOKEN:
            expected = "DISCORD_TOKEN" if cls.ENV == "prod" else "DEV_DISCORD_TOKEN"
            raise ValueError(f"❌ {expected} not found in secrets.env")
        if not cls.OPENAI_API_KEY:
            raise ValueError("❌ OpenAI API key not found in secrets.env")
    
    @classmethod
    def get_discord_intents(cls):
        """Get configured Discord intents"""
        import discord
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.message_content = True
        return intents 