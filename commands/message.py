# File: commands/message.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import commissioner_only, subscription_required, ALL_PREMIUM_SKUS
from utils.command_logger import log_command

def setup_message_commands(bot: commands.Bot):
    message_group = app_commands.Group(name="message", description="League announcements and messaging")

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @message_group.command(name="custom", description="Send a custom message to up to 5 selected channels.")
    @app_commands.describe(
        message="The message to send to the channels.",
        channel_1="Select the first channel.",
        mention_roles="Mention roles by name, ID, or @Role (comma separated).",
        mention_users="Mention users by @mention or ID (space separated).",
        channel_2="Select the second channel (optional).",
        channel_3="Select the third channel (optional).",
        channel_4="Select the fourth channel (optional).",
        channel_5="Select the fifth channel (optional)."
    )
    @log_command("message custom")
    async def send_message(
        interaction: discord.Interaction,
        message: str,
        channel_1: str,
        mention_roles: str = "",
        mention_users: str = "",
        channel_2: str = None,
        channel_3: str = None,
        channel_4: str = None,
        channel_5: str = None
    ):

        # Get the guild where the command was used
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.")
            return

        # Resolve roles to mention
        role_mentions = []
        invalid_roles = []
        if mention_roles:
            for raw_role in mention_roles.split(","):
                token = raw_role.strip()
                if not token:
                    continue

                role = None
                if token.startswith("<@&") and token.endswith(">"):
                    role_id = token[3:-1]
                    if role_id.isdigit():
                        role = guild.get_role(int(role_id))
                elif token.isdigit():
                    role = guild.get_role(int(token))
                else:
                    role = discord.utils.get(guild.roles, name=token)

                if role:
                    role_mentions.append(role.mention)
                else:
                    invalid_roles.append(token)

        if mention_roles and not role_mentions:
            await interaction.response.send_message(
                "No valid roles were found. Please check the role names or mentions and try again.",
                ephemeral=True
            )
            return

        # Resolve users to mention
        user_mentions = []
        invalid_users = []
        if mention_users:
            for entry in mention_users.split():
                token = entry.strip()
                if not token:
                    continue

                member = None
                if token.startswith("<@") and token.endswith(">"):
                    user_id_str = token[2:-1].replace("!", "")
                    if user_id_str.isdigit():
                        member = guild.get_member(int(user_id_str))
                elif token.isdigit():
                    member = guild.get_member(int(token))
                else:
                    member = discord.utils.find(
                        lambda m: m.name.lower() == token.lower() or m.display_name.lower() == token.lower(),
                        guild.members
                    )

                if member:
                    user_mentions.append(member.mention)
                else:
                    invalid_users.append(token)

        if mention_users and not user_mentions:
            await interaction.response.send_message(
                "No valid users were found to mention. Please check the values provided.",
                ephemeral=True
            )
            return

        # Collect the selected channels
        channel_names = [channel_1, channel_2, channel_3, channel_4, channel_5]
        channel_names = [name for name in channel_names if name]  # Filter out None values

        # Resolve channel objects, ensuring only text channels are selected
        channels = [
            discord.utils.get(guild.text_channels, name=name)
            for name in channel_names
        ]

        # Check for invalid channels
        invalid_channels = [name for name, channel in zip(channel_names, channels) if not channel]
        if invalid_channels:
            await interaction.response.send_message(
                f"The following channels were not found or are not text channels: {', '.join(invalid_channels)}",
                ephemeral=True
            )
            return

        mention_prefix = " ".join(role_mentions + user_mentions).strip()
        content_to_send = f"{mention_prefix} {message}".strip() if mention_prefix else message

        # Send the message to the valid channels
        for channel in channels:
            if channel:
                await channel.send(content_to_send)

        response_parts = [f"Message sent to the following channels: {', '.join(channel_names)}."]
        if role_mentions:
            response_parts.append(f"Roles mentioned: {', '.join(role_mentions)}.")
        if user_mentions:
            response_parts.append(f"Users mentioned: {', '.join(user_mentions)}.")
        if invalid_roles:
            response_parts.append(f"⚠️ Could not find roles: {', '.join(invalid_roles)}.")
        if invalid_users:
            response_parts.append(f"⚠️ Could not find users: {', '.join(invalid_users)}.")

        await interaction.response.send_message("\n".join(response_parts))

    # Autocomplete for each channel parameter
    async def text_channel_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        # Filter text channels based on user input
        matching_channels = [
            channel.name for channel in guild.text_channels
            if current.lower() in channel.name.lower()
        ]

        # Return up to 10 matching channel names for selection
        return [
            discord.app_commands.Choice(name=channel, value=channel)
            for channel in matching_channels[:10]
        ]

    # Add autocomplete to each channel parameter
    send_message.autocomplete("channel_1")(text_channel_autocomplete)
    send_message.autocomplete("channel_2")(text_channel_autocomplete)
    send_message.autocomplete("channel_3")(text_channel_autocomplete)
    send_message.autocomplete("channel_4")(text_channel_autocomplete)
    send_message.autocomplete("channel_5")(text_channel_autocomplete)

    @send_message.autocomplete("mention_roles")
    async def mention_roles_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        matching_roles = [
            role for role in guild.roles if current.lower() in role.name.lower()
        ]

        return [
            discord.app_commands.Choice(name=role.name, value=role.name)
            for role in matching_roles[:10]
        ]

    @send_message.autocomplete("mention_users")
    async def mention_users_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        matching_members = [
            member for member in guild.members
            if current.lower() in member.display_name.lower() or current.lower() in member.name.lower()
        ]

        return [
            discord.app_commands.Choice(name=member.display_name, value=member.mention)
            for member in matching_members[:10]
        ]


    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @message_group.command(name="announce-advance", description="@role. Week _ is here. Next Advance is _")
    @app_commands.describe(
        week="Specify the week number or name.",
        next_advance="Specify the next advance time for the week.",
        mention_roles="Select roles to notify.",
        channel_1="Select the first channel to send the message.",
        channel_2="Select the second channel to send the message.",
        channel_3="Select the third channel to send the message.",
        channel_4="Select the fourth channel to send the message.",
        channel_5="Select the fifth channel to send the message.",
        custom_message="Add a custom message to include at the end of the announcement."
    )
    @log_command("message announce-advance")
    async def announce_week_advanced(
        interaction: discord.Interaction,
        week: str,
        next_advance: str,
        mention_roles: str,
        channel_1: str,
        channel_2: str = None,
        channel_3: str = None,
        channel_4: str = None,
        channel_5: str = None,
        custom_message: str = ""
    ):
        guild = interaction.guild

        # Build role mentions
        roles_to_mention = []
        for role_name in mention_roles.split(","):
            role = discord.utils.get(guild.roles, name=role_name.strip())
            if role:
                roles_to_mention.append(role.mention)

        if not roles_to_mention:
            await interaction.response.send_message("Please specify valid roles.", ephemeral=True)
            return

        role_mentions = " ".join(roles_to_mention)

        # Format week intelligently
        if week.strip().isdigit():
            display_week = f"Week {week.strip()}"
        else:
            display_week = week.strip()

        embed = discord.Embed(
            title=f"📣 League Advanced To {display_week}",
            color=discord.Color.blurple()
        )

        embed.add_field(name="Next Advance", value=next_advance, inline=True)
        if custom_message:
            embed.add_field(name="Commissioner Message", value=custom_message, inline=False)

        # Channels
        channel_names = [channel_1, channel_2, channel_3, channel_4, channel_5]
        sent_channels = []

        for channel_name in channel_names:
            if channel_name:
                channel = discord.utils.get(guild.text_channels, name=channel_name.strip())
                if channel:
                    await channel.send(content=role_mentions, embed=embed)
                    sent_channels.append(channel_name)

        if sent_channels:
            confirm_embed = discord.Embed(
                title="✅ Announcement Sent",
                description=f"Advance announcement for **{week}** delivered to the selected channels.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Channels",
                value="\n".join(f"• {ch}" for ch in sent_channels),
                inline=False
            )
            await interaction.response.send_message(embed=confirm_embed)
        else:
            await interaction.response.send_message("No valid channels were specified or found.", ephemeral=True)



    # Autocomplete for roles (modified to handle multiple roles)
    @announce_week_advanced.autocomplete("mention_roles")
    async def mention_roles_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        # Get matching roles based on the input
        matching_roles = [
            role.name for role in guild.roles if current.lower() in role.name.lower()
        ]

        # Limit to top 10 matches
        return [
            discord.app_commands.Choice(name=role, value=role)
            for role in matching_roles[:10]
        ]

    # Autocomplete for each channel
    @announce_week_advanced.autocomplete("channel_1")
    @announce_week_advanced.autocomplete("channel_2")
    @announce_week_advanced.autocomplete("channel_3")
    @announce_week_advanced.autocomplete("channel_4")
    @announce_week_advanced.autocomplete("channel_5")
    async def channels_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        # Get matching channels based on the current input
        matching_channels = [
            channel.name for channel in guild.text_channels if current.lower() in channel.name.lower()
        ]

        # Limit to top 5 matches
        return [
            discord.app_commands.Choice(name=channel, value=channel)
            for channel in matching_channels[:5]
        ]

    # Overview command removed - use /help feature message instead

    bot.tree.add_command(message_group)