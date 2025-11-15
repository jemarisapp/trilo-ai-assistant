"""
Help command module for Trilo Bot
Consolidates all overview information with filtering by feature and audience
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.command_logger import log_command

def setup_help_commands(bot: commands.Bot):
    trilo_group = app_commands.Group(name="trilo", description="Trilo Bot commands")

    @trilo_group.command(name="help", description="Get help with Trilo Bot features")
    @app_commands.describe(
        feature="The feature to get help with",
        audience="Who this help is for (commissioners, members, or all)"
    )
    @app_commands.choices(
        feature=[
            app_commands.Choice(name="Getting Started & Overview", value="overview"),
            app_commands.Choice(name="Admin & Server Management", value="admin"),
            app_commands.Choice(name="Team Management", value="teams"),
            app_commands.Choice(name="Matchup Automation", value="matchups"),
            app_commands.Choice(name="Messaging Tools", value="message"),
            app_commands.Choice(name="Attribute Point System", value="attributes"),
            app_commands.Choice(name="Win/Loss Records", value="records"),
            app_commands.Choice(name="Settings", value="settings")
        ],
        audience=[
            app_commands.Choice(name="Everyone", value="all"),
            app_commands.Choice(name="Commissioners", value="commissioners"),
            app_commands.Choice(name="League Members", value="members")
        ]
    )
    @log_command("trilo help")
    async def trilo_help(interaction: discord.Interaction, feature: str, audience: str):
        """Show help for a specific feature with audience filtering"""
        
        if feature == "overview":
            # Show comprehensive overview (no audience filtering needed for overview)
            embeds = get_comprehensive_overview()
        else:
            # Show targeted help for specific features
            # Always start with command usage instructions
            embeds = [get_command_usage_embed()]
            
            if feature == "admin":
                embeds.extend(get_admin_help(audience))
            elif feature == "teams":
                embeds.extend(get_teams_help(audience))
            elif feature == "matchups":
                embeds.extend(get_matchups_help(audience))
            elif feature == "message":
                embeds.extend(get_message_help(audience))
            elif feature == "attributes":
                embeds.extend(get_attributes_help(audience))
            elif feature == "records":
                embeds.extend(get_records_help(audience))
            elif feature == "settings":
                embeds.extend(get_settings_help(audience))
            else:
                await interaction.response.send_message("❌ Invalid feature selected.", ephemeral=True)
                return

        await interaction.response.send_message(embeds=embeds, ephemeral=False)

    bot.tree.add_command(trilo_group)

def get_command_usage_embed():
    """Get the command usage instructions embed"""
    embed = discord.Embed(
        title="💡 How to Use Commands",
        description=(
            "**💡 To use a command, type `/` and begin typing its name.**\n"
            "**🎮 Or tap the Discord Controller icon (next to your keyboard) to browse available options and use the built-in forms.**\n\n"
            "💬 Need help? Use `/trilo help` for detailed guidance"
        ),
        color=discord.Color.teal()
    )
    return embed

def get_comprehensive_overview():
    """Get comprehensive overview of all Trilo features (from /trilo command)"""
    embeds = []
    
    # Getting Started & Overview embed
    embed0 = discord.Embed(
        title="📘 Getting Started & Overview",
        description=(
            "💡 *To use a command, type `/` and begin typing its name.*\n"
            "🎮 *Or tap the Discord Controller icon (next to your keyboard) to browse available options and use the built-in forms.*\n\n"
            "**Quick Start:**\n"
            "• `/admin trial` — Start 10-day free trial\n"
            "• `/teams assign-user` — Assign team owners\n"
            "• `/matchups create` — Auto-generate weekly matchups\n"
            "• `/settings set` — Configure commissioner roles\n\n"
            "🧠 For a detailed walkthrough, use `/admin guide`\n"
            "💬 Need help? Use `/trilo help` for detailed guidance"
        ),
        color=discord.Color.teal()
    )
    embeds.append(embed0)

    # Admin & Server Management
    embed1 = discord.Embed(
        title="🔐 Admin & Server Management",
        description=(
            "• `/admin trial` — Start 10-day trial\n"
            "• `/admin purchase` — View premium plans\n"
            "• `/admin activate-annual` — Activate annual subscription\n"
            "• `/admin check-subscription` — Check subscription status\n"
            "• `/admin setup-league` — Create league structure\n"
            "• `/admin guide` — Setup walkthrough"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed1)

    # Server Settings
    embed2 = discord.Embed(
        title="⚙️ Server Settings",
        description=(
            "• `/settings help` — Settings usage guide\n"
            "• `/settings set` — Configure server settings\n"
            "• `/settings view` — See current settings\n"
            "• `/settings reset` — Remove a setting\n"
            "• `/settings clear-all` — Wipe all settings\n\n"
            "**Available Settings:**\n"
            "• `commissioner_roles` — Set roles for commissioner commands\n"
            "• `record_tracking_enabled` — Enable/disable automatic record tracking\n"
            "• `attributes_log_channel` — Channel for attribute change logs\n"
            "• `stream_notify_role` — Role to ping for stream announcements\n"
            "• `stream_watch_channel` — Channel for stream notifications\n"
            "• `stream_announcements_enabled` — Enable/disable stream features"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed2)

    # Team Management
    embed3 = discord.Embed(
        title="📝 Team Management",
        description=(
            "• `/trilo help` — Team system guide\n"
            "• `/teams assign-user` — Assign a user to a team\n"
            "• `/teams unassign-user` — Remove a user from a team\n"
            "• `/teams clear-team` — Unassign a team\n"
            "• `/teams list-all` — See all assignments\n"
            "• `/teams who-has` — Check who owns a team\n"
            "• `/teams clear-all-assignments` — Wipe all assignments"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed3)

    # Matchup Automation
    embed4 = discord.Embed(
        title="📆 Matchup Automation",
        description=(
            "• `/trilo help` — Matchup system guide\n"
            "• `/matchups cfb-create-from-image` — Create from schedule images\n"
            "• `/matchups cfb-create-from-text` — Create matchups manually\n"
            "• `/matchups tag-users` — Tag users in their games\n"
            "• `/matchups list-all` — View all matchups\n"
            "• `/matchups delete` — Delete matchup categories (with option to keep categories for reuse)\n"
            "• `/matchups sync-records` — Update with current records\n"
            "• `/matchups make-public` — Make category public\n"
            "• `/matchups make-private` — Make category private\n"
            "• `/matchups add-game-status` — Add outcome tracking"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed4)

    # Messaging Tools
    embed5 = discord.Embed(
        title="📣 Messaging Tools",
        description=(
            "• `/trilo help` — Messaging system guide\n"
            "• `/message custom` — Send message to channels\n"
            "• `/message announce-advance` — Notify of next advance time"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed5)

    # Attribute Point System
    embed6 = discord.Embed(
        title="📊 Attribute Point System (Pro Only)",
        color=discord.Color.gold()
    )
    embed6.add_field(
        name="For Users",
        value=(
            "• `/trilo help` — Points system guide\n"
            "• `/attributes my-points` — Check your balance\n"
            "• `/attributes request` — Request player upgrade\n"
            "• `/attributes cancel-request` — Cancel pending request\n"
            "• `/attributes requests-history` — View your history"
        ),
        inline=False
    )
    embed6.add_field(
        name="For Commissioners",
        value=(
            "• `/trilo help` — Points system guide\n"
            "• `/attributes give` — Award points to users\n"
            "• `/attributes approve-request` — Approve upgrade request\n"
            "• `/attributes approve-all` — Approve all pending requests\n"
            "• `/attributes deny-request` — Deny upgrade request\n"
            "• `/attributes deny-all` — Deny all pending requests\n"
            "• `/attributes revoke` — Remove points from user\n"
            "• `/attributes revoke-all-from-user` — Reset user to 0\n"
            "• `/attributes check-user` — Check user's points\n"
            "• `/attributes check-all` — View all point balances\n"
            "• `/attributes requests-list` — View pending requests\n"
            "• `/attributes requests-history` — View any user's history\n"
            "• `/attributes clear-all` — Wipe all points"
        ),
        inline=False
    )
    embeds.append(embed6)

    # Win/Loss Records
    embed7 = discord.Embed(
        title="🏆 Win/Loss Records",
        description=(
            "• `/trilo help` — Records system guide\n"
            "• `/records check-record` — Check team's record\n"
            "• `/records view-all-records` — View all records\n"
            "• `/records set-record` — Manually set record\n"
            "• `/records clear-team-record` — Clear team record\n"
            "• `/records clear-all` — Wipe all records"
        ),
        color=discord.Color.gold()
    )
    embeds.append(embed7)

    # Subscription Tiers
    embed8 = discord.Embed(
        title="💎 Subscription Tiers",
        description=(
            "**💎 Subscription Tiers:**\n"
            "**🔸 Pro Tier**: Team Management, Matchups, Messaging, Settings, Win/Loss Records + Attribute Points\n\n"
            "Upgrade at `/admin purchase` or start a trial with `/admin trial`"
        ),
        color=discord.Color.purple()
    )
    embeds.append(embed8)

    return embeds

def get_admin_help(audience: str):
    """Get admin help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="🔐 Admin & Server Management",
            description=(
                "Essential commands for setting up and managing your Trilo bot instance.\n\n"
                "**Setup Commands:**\n"
                "• `/admin trial` — Start 10-day trial\n"
                "• `/admin purchase` — View premium plans\n"
                "• `/admin activate-annual` — Activate annual subscription\n"
                "• `/admin check-subscription` — Check subscription status\n"
                "• `/admin setup-league` — Create league structure\n"
                "• `/admin guide` — Setup walkthrough\n\n"
                "**Subscription Management:**\n"
                "• `/admin purchase` — View premium plans\n"
                "• `/admin trial` — Start 10-day trial\n"
                "• `/admin activate-annual` — Activate annual subscription\n"
                "• `/admin check-subscription` — Check subscription status"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed)
    
    if audience in ["all", "members"]:
        embed = discord.Embed(
            title="🔐 Admin & Server Management",
            description=(
                "Information about Trilo's setup and subscription options.\n\n"
                "**Getting Started:**\n"
                "• `/admin guide` — Setup walkthrough\n"
                "• `/admin purchase` — View premium plans\n"
                "• `/admin trial` — Start 10-day trial\n"
                "• `/admin check-subscription` — Check subscription status\n\n"
                "💡 *Contact your server administrator to activate Trilo with an access key.*"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed)
    
    return embeds

def get_teams_help(audience: str):
    """Get teams help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "members"]:
        embed = discord.Embed(
            title="📝 Team Management - For All Users",
            description=(
                "Check team assignments and ownership information.\n\n"
                "**Available Commands:**\n"
                "• `/teams who-has` — Check who owns a team\n"
                "• `/teams list-all` — See all team assignments"
            ),
            color=discord.Color.from_str("#f2c94c")
        )
        embeds.append(embed)
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="📝 Team Management - For Commissioners",
            description=(
                "Manage team assignments and ownership for your league.\n\n"
                "**Management Commands:**\n"
                "• `/teams assign-user` — Assign a user to a team\n"
                "• `/teams unassign-user` — Remove a user from their team\n"
                "• `/teams clear-team` — Clear a team's user assignment\n"
                "• `/teams clear-all-assignments` — Wipe all team assignments\n\n"
                "**Viewing Commands:**\n"
                "• `/teams list-all` — See all team-user pairings"
            ),
            color=discord.Color.from_str("#e2b007")
        )
        embeds.append(embed)
    
    return embeds

def get_matchups_help(audience: str):
    """Get matchups help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "members"]:
        embed = discord.Embed(
            title="📆 Matchup Automation - For All Users",
            description=(
                "View and interact with league matchups.\n\n"
                "**Available Commands:**\n"
                "• `/matchups list-all` — View all matchups and who's playing who\n\n"
                "**Game Interaction:**\n"
                "• Use reactions in matchup channels to mark game status:\n"
                "  ✅ Completed, 🎲 Fair Sim, ☑️ Force Win"
            ),
            color=discord.Color.from_str("#f2c94c")
        )
        embeds.append(embed)
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="📆 Matchup Automation - For Commissioners",
            description=(
                "Create, manage, and track league matchups directly inside Discord.\n\n"
                "**Creation & Management:**\n"
                "• `/matchups create` — Create new matchup channels under a category\n"
                "• `/matchups cfb-create-from-image` — Create matchups by uploading schedule images\n"
                "• `/matchups delete` — Delete matchup categories (with option to keep categories for reuse)\n"
                "• `/matchups tag-users` — Auto-tag users based on matchups\n"
                "• `/matchups sync-records` — Refresh matchups to show up-to-date records\n\n"
                "**Visibility Control:**\n"
                "• `/matchups make-public` — Make all matchups in a category visible\n"
                "• `/matchups make-private` — Restrict category visibility to certain roles\n\n"
                "**Game Tracking:**\n"
                "• `/matchups add-game-status` — Add or refresh game status messages\n"
                "• Game results may include win/loss records if record tracking is enabled"
            ),
            color=discord.Color.from_str("#e2b007")
        )
        embeds.append(embed)
    
    return embeds

def get_message_help(audience: str):
    """Get message help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="📣 Messaging Tools",
            description=(
                "Send announcements and notifications to your league.\n\n"
                "**Available Commands:**\n"
                "• `/message custom` — Send custom message to channels\n"
                "• `/message announce-advance` — Notify of next advance time\n\n"
                "💡 *Use these tools to keep your league informed and engaged.*"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed)
    
    return embeds

def get_attributes_help(audience: str):
    """Get attributes help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "members"]:
        embed = discord.Embed(
            title="📊 Attribute Point System - For Users",
            description=(
                "Request player upgrades and manage your attribute points.\n\n"
                "**Available Commands:**\n"
                "• `/attributes my-points` — Check your balance\n"
                "• `/attributes request` — Request player upgrade\n"
                "• `/attributes cancel-request` — Cancel pending request\n"
                "• `/attributes requests-history` — View your history\n\n"
                "💡 *Commissioners must approve all upgrade requests.*"
            ),
            color=discord.Color.from_str("#f2c94c")
        )
        embeds.append(embed)
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="📊 Attribute Point System - For Commissioners",
            description=(
                "Manage the attribute point system and approve upgrade requests.\n\n"
                "**Point Management:**\n"
                "• `/attributes give` — Award points to users\n"
                "• `/attributes revoke` — Remove points from user\n"
                "• `/attributes revoke-all-from-user` — Reset user to 0\n"
                "• `/attributes clear-all` — Wipe all points\n\n"
                                        "**Request Management:**\n"
            "• `/attributes approve-request` — Approve upgrade request\n"
            "• `/attributes approve-all` — Approve all pending requests\n"
            "• `/attributes deny-request` — Deny upgrade request\n"
            "• `/attributes deny-all` — Deny all pending requests\n"
            "• `/attributes requests-list` — View pending requests\n"
                "• `/attributes requests-history` — View any user's history\n\n"
                "**Information Commands:**\n"
                "• `/attributes check-user` — Check user's points\n"
                "• `/attributes check-all` — View all point balances"
            ),
            color=discord.Color.from_str("#e2b007")
        )
        embeds.append(embed)
    
    return embeds

def get_records_help(audience: str):
    """Get records help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "members"]:
        embed = discord.Embed(
            title="🏆 Win/Loss Records - For All Users",
            description=(
                "View league standings and team records.\n\n"
                "**Available Commands:**\n"
                "• `/records check-record` — Check team's record\n"
                "• `/records view-all-records` — View all records\n\n"
                "💡 *Records are automatically updated when commissioners use matchup tools.*"
            ),
            color=discord.Color.from_str("#f2c94c")
        )
        embeds.append(embed)
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="🏆 Win/Loss Records - For Commissioners",
            description=(
                "Manage win/loss records for your league teams.\n\n"
                "**Management Commands:**\n"
                "• `/records set-record` — Manually set record\n"
                "• `/records clear-team-record` — Clear team record\n"
                "• `/records clear-all` — Wipe all records\n\n"
                "**Viewing Commands:**\n"
                "• `/records check-record` — Check team's record\n"
                "• `/records view-all-records` — View all records\n\n"
                "💡 *Records can be automatically synced with matchups when enabled.*"
            ),
            color=discord.Color.from_str("#e2b007")
        )
        embeds.append(embed)
    
    return embeds

def get_settings_help(audience: str):
    """Get settings help embeds based on audience"""
    embeds = []
    
    if audience in ["all", "commissioners"]:
        embed = discord.Embed(
            title="⚙️ Server Settings",
            description=(
                "Configure Trilo's behavior and features for your server.\n\n"
                "**Available Commands:**\n"
                "• `/settings help` — Settings usage guide\n"
                "• `/settings set` — Configure server settings\n"
                "• `/settings view` — See current settings\n"
                "• `/settings reset` — Remove a setting\n"
                "• `/settings clear-all` — Wipe all settings\n\n"
                "**Available Settings:**\n"
                "• `commissioner_roles` — Set roles for commissioner commands\n"
                "• `record_tracking_enabled` — Enable/disable automatic record tracking\n"
                "• `attributes_log_channel` — Channel for attribute change logs\n"
                "• `stream_notify_role` — Role to ping for stream announcements\n"
                "• `stream_watch_channel` — Channel for stream notifications\n"
                "• `stream_announcements_enabled` — Enable/disable stream features"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed)
    
    return embeds
