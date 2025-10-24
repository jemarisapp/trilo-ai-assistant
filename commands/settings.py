import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.utils import get_db_connection
from utils.common import commissioner_only, subscription_required, ALL_PREMIUM_SKUS
from typing import Union
from utils.command_logger import log_command


def get_server_setting(server_id: str, setting: str) -> Union[str, None]:
    """Get a server setting value from database, return None if not set"""
    with get_db_connection("keys") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT new_value FROM server_settings
                WHERE server_id = ? AND setting = ?
            """,
            (server_id, setting),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else None


def is_record_tracking_enabled(server_id: str) -> bool:
    with get_db_connection("keys") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT new_value FROM server_settings
            WHERE server_id = ? AND setting = 'record_tracking_enabled'
        """, (server_id,))
        row = cursor.fetchone()
        return row and row[0].strip().lower() == "on"


def get_commissioner_roles(server_id: str) -> set:
    """Get commissioner roles from database, fallback to default if not set"""
    with get_db_connection("keys") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT new_value FROM server_settings
            WHERE server_id = ? AND setting = 'commissioner_roles'
        """, (server_id,))
        row = cursor.fetchone()
        
        if row and row[0]:
            # Parse comma-separated roles from database
            roles = {role.strip() for role in row[0].split(",")}
            return roles
        else:
            # Fallback to default roles
            return {"Commish", "Commissioners", "Commissioner", "commish", "commissioners", "commissioner"}


def setup_settings_commands(bot: commands.Bot):
    settings_group = app_commands.Group(name="settings", description="Customize server-level settings")

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @settings_group.command(name="set", description="Set a server setting...")
    @app_commands.rename(setting="setting", new_value="new_value")
    @app_commands.describe(
        setting="Which setting to update",
        new_value="New value (e.g., Commish,Admin or #channel)"
    )
    @log_command("settings set")
    async def set_setting(
        interaction: discord.Interaction,
        setting: Literal[
            "commissioner_roles",
            "record_tracking_enabled",
            "league_type",
            "attributes_log_channel",
            "stream_notify_role",                  # ✅ NEW
            "stream_watch_channel",                # ✅ NEW
            "stream_announcements_enabled"         # ✅ NEW
        ],
        new_value: str
    ):


        server_id = str(interaction.guild.id)

        # Safely parse and store the new_value
        if setting in {"attributes_log_channel", "stream_watch_channel"}:
            if new_value.startswith("<#") and new_value.endswith(">"):
                value_to_store = new_value.strip("<#>")
            elif new_value.isdigit():
                value_to_store = new_value
            else:
                await interaction.response.send_message(
                    "❌ Invalid channel format. Please mention a channel like `#attributes-log` or provide a channel ID.",
                    ephemeral=True
                )
                return
            
            # Validate that the channel exists
            try:
                channel = interaction.guild.get_channel(int(value_to_store))
                if not channel:
                    await interaction.response.send_message(
                        f"❌ Channel with ID `{value_to_store}` not found in this server.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid channel ID format.",
                    ephemeral=True
                )
                return
        elif setting == "commissioner_roles":
            # Validate that the roles exist
            role_names = [role.strip() for role in new_value.split(",")]
            existing_roles = []
            for role_name in role_names:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if not role:
                    await interaction.response.send_message(
                        f"❌ Role `{role_name}` not found in this server.",
                        ephemeral=True
                    )
                    return
                existing_roles.append(role_name)
            value_to_store = ",".join(existing_roles)
        elif setting == "league_type":
            # Validate league_type to be cfb or nfl only
            normalized = new_value.strip().lower()
            if normalized not in {"cfb", "nfl"}:
                await interaction.response.send_message(
                    "❌ Invalid league type. Use `cfb` or `nfl`.",
                    ephemeral=True
                )
                return
            value_to_store = normalized
        elif setting == "stream_notify_role":
            # Validate that the role exists
            role = discord.utils.get(interaction.guild.roles, name=new_value.strip())
            if not role:
                await interaction.response.send_message(
                    f"❌ Role `{new_value.strip()}` not found in this server.",
                    ephemeral=True
                )
                return
            value_to_store = new_value.strip()
        else:
            value_to_store = new_value.strip()
            
        if setting == "record_tracking_enabled" and new_value.lower() not in {"on", "off"}:
            await interaction.response.send_message("⚠️ Please use `on` or `off` for record tracking.", ephemeral=True)
            return


        # Insert or update the setting
        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO server_settings (server_id, setting, new_value, created_at, updated_at)
                VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                ON CONFLICT(server_id, setting) DO UPDATE SET new_value = excluded.new_value, updated_at = datetime('now', 'localtime')
            """, (server_id, setting, value_to_store))
            conn.commit()

        if setting in {"attributes_log_channel", "stream_watch_channel"}:
            channel = interaction.guild.get_channel(int(value_to_store))
            display_value = channel.mention if channel else f"`{value_to_store}`"
        elif setting == "record_tracking_enabled":
            display_value = "✅ ON" if value_to_store.lower() == "on" else "❌ OFF"
        elif setting == "league_type":
            display_value = "CFB" if value_to_store.lower() == "cfb" else "NFL"
        elif setting == "stream_announcements_enabled":
            display_value = "✅ ON" if value_to_store.lower() == "on" else "❌ OFF"
        elif setting in {"commissioner_roles", "stream_notify_role"}:
            display_value = f"`{value_to_store}`"
        else:
            display_value = f"`{value_to_store}`"


        await interaction.response.send_message(
            f"✅ Setting `{setting}` updated to {display_value}.",
            ephemeral=False
        )

    @set_setting.autocomplete("new_value")
    async def autocomplete_new_value(interaction: discord.Interaction, current: str):
        if interaction.namespace.setting == "attributes_log_channel":
            return [
                discord.app_commands.Choice(name=f"#{c.name}", value=str(c.id))
                for c in interaction.guild.text_channels
                if current.lower() in c.name.lower()
            ][:10]

        elif interaction.namespace.setting == "record_tracking_enabled":
            return [
                discord.app_commands.Choice(name="✅ ON", value="on"),
                discord.app_commands.Choice(name="❌ OFF", value="off"),
            ]

        elif interaction.namespace.setting == "league_type":
            return [
                discord.app_commands.Choice(name="CFB", value="cfb"),
                discord.app_commands.Choice(name="NFL", value="nfl"),
            ]

        elif interaction.namespace.setting == "commissioner_roles":
            return [
                discord.app_commands.Choice(name=role.name, value=role.name)
                for role in interaction.guild.roles
                if current.lower() in role.name.lower() and role.name != "@everyone"
            ][:10]

        elif interaction.namespace.setting == "stream_watch_channel":
            return [
                discord.app_commands.Choice(name=f"#{c.name}", value=str(c.id))
                for c in interaction.guild.text_channels
                if current.lower() in c.name.lower()
            ][:10]

        elif interaction.namespace.setting == "stream_notify_role":
            return [
                discord.app_commands.Choice(name=role.name, value=role.name)
                for role in interaction.guild.roles
                if current.lower() in role.name.lower() and role.name != "@everyone"
            ][:10]

        elif interaction.namespace.setting == "stream_announcements_enabled":
            return [
                discord.app_commands.Choice(name="✅ ON", value="on"),
                discord.app_commands.Choice(name="❌ OFF", value="off"),
            ]

        return []

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @settings_group.command(name="view", description="View all current server settings.")
    @log_command("settings view")
    async def view_settings(interaction: discord.Interaction):
        server_id = str(interaction.guild.id)

        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting, new_value FROM server_settings
                WHERE server_id = ?
            """, (server_id,))
            settings = cursor.fetchall()

        if not settings:
            await interaction.response.send_message("⚙️ This server has no custom settings yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⚙️ Server Settings",
            color=discord.Color.blue()
        )

        for setting, value in settings:
            if setting == "record_tracking_enabled":
                display_value = "✅ ON" if value.lower() == "on" else "❌ OFF"
            elif setting == "league_type":
                display_value = "CFB" if value.lower() == "cfb" else "NFL"
            elif setting == "stream_announcements_enabled":
                display_value = "✅ ON" if value.lower() == "on" else "❌ OFF"
            elif setting in {"attributes_log_channel", "stream_watch_channel"}:
                channel = interaction.guild.get_channel(int(value))
                display_value = channel.mention if channel else f"`{value}`"
            elif setting == "stream_notify_role":
                display_value = f"`{value}`"
            else:
                display_value = f"`{value}`"


            embed.add_field(name=setting, value=display_value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @settings_group.command(name="reset", description="Remove a specific setting from this server.")
    @app_commands.describe(
        setting="The setting you want to reset"
    )
    @log_command("settings reset")
    async def reset_setting(interaction: discord.Interaction,
        setting: Literal[
            "commissioner_roles",
            "record_tracking_enabled",
            "league_type",
            "attributes_log_channel",
            "stream_notify_role",
            "stream_watch_channel",
            "stream_announcements_enabled"
        ]):

        server_id = str(interaction.guild.id)

        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM server_settings WHERE server_id = ? AND setting = ?", (server_id, setting))
            conn.commit()

        await interaction.response.send_message(f"🗑️ Setting `{setting}` has been reset.", ephemeral=False)


    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @settings_group.command(name="clear-all", description="Remove all settings for this server.")
    @log_command("settings clear-all")
    async def clear_all_settings(interaction: discord.Interaction):

        server_id = str(interaction.guild.id)

        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM server_settings WHERE server_id = ?", (server_id,))
            conn.commit()

        await interaction.response.send_message("🧹 All settings for this server have been cleared.", ephemeral=False)


    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @settings_group.command(name="help", description="Learn how each setting works.")
    @log_command("settings help")
    async def settings_help(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Settings Help",
            description="Here's what each setting controls and how to use it.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="`commissioner_roles`",
            value=(
                "Comma-separated list of role names that can access commissioner-only commands like `/teams`, & `/matchups`.\n"
                "**Example:** `/settings set setting:commissioner_roles new_value:Commish,Admin`\n"
                "🔐 Only server administrators can update this."
            ),
            inline=False
        )

        embed.add_field(
            name="`record_tracking_enabled`",
            value=(
                "Enable or disable automatic record tracking for teams.\n"
                "**Example:** `/settings set setting:record_tracking_enabled new_value:on`\n"
                "📊 When enabled, team records are automatically updated after games."
            ),
            inline=False
        )
        embed.add_field(
            name="`league_type`",
            value=(
                "Set the default league for commands and autocompletes (CFB or NFL).\n"
                "**Example:** `/settings set setting:league_type new_value:cfb`\n"
                "🏈 Defaults to CFB if not set."
            ),
            inline=False
        )
        embed.add_field(
            name="`attributes_log_channel`",
            value=(
                "Channel ID where attribute changes are logged.\n"
                "**Example:** `/settings set setting:attributes_log_channel new_value:#attributes-log`\n"
                "📝 Optional logging for attribute modifications."
            ),
            inline=False
        )
        embed.add_field(
            name="`stream_notify_role`",
            value=(
                "Role to mention when stream notifications are sent.\n"
                "**Example:** `/settings set setting:stream_notify_role new_value:Streamers`\n"
                "🔔 Role that gets pinged for stream announcements."
            ),
            inline=False
        )
        embed.add_field(
            name="`stream_watch_channel`",
            value=(
                "Channel where stream announcements are posted.\n"
                "**Example:** `/settings set setting:stream_watch_channel new_value:#streams`\n"
                "📺 Channel for stream notifications and announcements."
            ),
            inline=False
        )
        embed.add_field(
            name="`stream_announcements_enabled`",
            value=(
                "Enable or disable stream announcement features.\n"
                "**Example:** `/settings set setting:stream_announcements_enabled new_value:on`\n"
                "🎮 Controls whether stream notifications are active."
            ),
            inline=False
        )
        embed.set_footer(text="Use /settings view to check current values.")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    bot.tree.add_command(settings_group)
