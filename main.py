"""
Main entry point for Trilo Discord Bot
"""
import asyncio
import logging
import discord
from src.bot import TriloBot
from src.events.reactions import handle_reaction_add
from src.events.messages import handle_message
from config.settings import BotSettings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    try:
        # Validate environment
        BotSettings.validate_environment()
        logger.info("✅ Environment validation passed")
        
        # Create and run bot
        bot = TriloBot()
        
        # Note: Manual cleanup available via scripts
        # Run: python3 data/scripts/trilo_auto_cleanup.py
        
        # Register event handlers
        @bot.event
        async def on_raw_reaction_add(payload):
            await handle_reaction_add(bot, payload)
        
        @bot.event
        async def on_message(message):
            await handle_message(bot, message)
            # Process slash commands
            await bot.process_commands(message)
        
                # /trilo command removed - use /trilo help overview instead
        
        # Run the bot
        logger.info("🚀 Starting Trilo Discord Bot...")
        bot.run(BotSettings.DISCORD_TOKEN)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main() 