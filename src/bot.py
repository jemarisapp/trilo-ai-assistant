"""
Main Trilo Discord Bot class
"""
import logging
import discord
from discord.ext import commands

from config.settings import BotSettings
from config.database import DatabaseConfig

class TriloBot(commands.Bot):
    """Main Trilo Discord Bot class"""
    
    def __init__(self):
        intents = BotSettings.get_discord_intents()
        super().__init__(
            command_prefix=BotSettings.COMMAND_PREFIX,
            intents=intents
        )
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        DatabaseConfig.ensure_data_dir()
    
    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        # Register all command groups
        await self._register_commands()
    
    async def _register_commands(self):
        """Register all command groups"""
        try:
            from commands.admin import setup_admin_commands
            from commands.teams import setup_team_commands
            from commands.matchups import setup_matchup_commands
            from commands.message import setup_message_commands
            from commands.points import setup_points_commands
            
            from commands.records import setup_records_commands
            from commands.settings import setup_settings_commands
            from commands.ability_lab import setup_ability_lab_commands
            from commands.help import setup_help_commands
            
            setup_admin_commands(self)
            setup_team_commands(self)
            setup_matchup_commands(self)
            setup_message_commands(self)
            setup_points_commands(self)
    
            setup_settings_commands(self)
            setup_records_commands(self)
            setup_ability_lab_commands(self)
            setup_help_commands(self)
            
            self.logger.info("✅ All command groups registered successfully")
        except Exception as e:
            self.logger.error(f"❌ Error registering commands: {e}")
            raise
    
    async def on_ready(self):
        """Called when bot is ready"""
        self.logger.info(f"Bot is ready. Logged in as {self.user}")
        
        try:
            synced = await self.tree.sync()
            total_commands = sum(1 for command in self.tree.walk_commands())
            self.logger.info(f"Synced {total_commands} command(s).")
        except Exception as e:
            self.logger.error(f"Error syncing commands: {e}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild"""
        try:
            if guild.owner:
                embed = discord.Embed(
                    title="🎉 Welcome to Trilo!",
                    description=(
                        "Thanks for adding Trilo to your server!\n\n"
                        "💡 To use a command, type `/` and begin typing its name.\n"
                        "🎮 Or tap the Discord Controller icon (next to your keyboard) to browse available options and use the built-in forms.\n\n"
                        "**Get started with these commands:**\n"
                        "• `/admin guide` — Step-by-step setup walkthrough\n"
                        "• `/trilo help` — View all features and commands\n\n"
                        f"**💬 Need help?**\n- Use `/trilo help` for detailed guidance\n- Or [join our Support Server]({BotSettings.SUPPORT_SERVER_URL})"
                    ),
                    color=discord.Color.green()
                )
                embed.set_footer(text="Trilo • The Dynasty League Assistant")

                await guild.owner.send(embed=embed)
                self.logger.info(f"✅ Sent welcome message to {guild.owner.name}")
        except Exception as e:
            self.logger.error(f"❌ Could not DM server owner in {guild.name}: {e}")
    
    async def on_member_remove(self, member: discord.Member):
        """Called when a member leaves the guild"""
        try:
            from utils import get_db_connection
            
            # Remove team assignment for this specific server only
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cfb_teams WHERE user_id = ? AND server_id = ?", (member.id, str(member.guild.id)))
                conn.commit()
                self.logger.info(f"Removed team assignment for user {member.id} ({member.name}) from server {member.guild.id}")

            # Remove attribute points
            with get_db_connection("attributes") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attribute_points WHERE user_id = ?", (member.id,))
                cursor.execute("DELETE FROM attribute_requests WHERE user_id = ?", (member.id,))
                conn.commit()
                self.logger.info(f"Removed attribute points and requests for user {member.id} ({member.name})")
        except Exception as e:
            self.logger.error(f"Error cleaning up data for user {member.id}: {e}") 
    
