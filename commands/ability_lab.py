from discord import Embed, Interaction
from discord.ext import commands
from discord import app_commands
import discord
from utils.command_logger import log_command

def setup_ability_lab_commands(bot: commands.Bot):
    @bot.tree.command(name="ability-lab", description="Access the Trilo Ability Lab Dashboard for ability information")
    @log_command("ability-lab")
    async def view_ability_lab(interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        
        # Create dashboard URL
        dashboard_url = "https://dynastylab.streamlit.app/"
        
        # Create beautiful purple embed
        embed = Embed(
            title="🏈 Trilo Ability Lab",
            description=(
                "Click the link above to access the full interactive dashboard with:\n\n"
                "• **AI Upgrade Assistant** - Get personalized upgrade advice\n"
                "• **Visual Ability Tiers** - See Bronze to Platinum progression\n"
                "• **SP Calculator** - Plan your skill point spending\n"
                "• **Detailed Analytics** - Compare archetypes and abilities\n"
                "• **Position & Archetype Filtering** - Browse by specific player types"
            ),
            color=discord.Color.purple(),
            url=dashboard_url
        )        
        # Send the embed
        await interaction.followup.send(embed=embed)
