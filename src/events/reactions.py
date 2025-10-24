"""
Reaction event handlers for Trilo Discord Bot
"""
import discord
from config.settings import BotSettings
from utils import get_db_connection, strip_status_suffix, apply_status_suffix, clean_team_key, format_team_name
from commands.settings import is_record_tracking_enabled, get_commissioner_roles

async def handle_reaction_add(bot, payload: discord.RawReactionActionEvent):
    """Handle reaction add events"""
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in BotSettings.VALID_REACTIONS:
        return

    guild = bot.get_guild(payload.guild_id)
    server_id = str(payload.guild_id)
    record_tracking = is_record_tracking_enabled(server_id)

    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return
        
    # Get commissioner roles from database
    commissioner_roles = get_commissioner_roles(server_id)
    user_roles = {role.name for role in member.roles}
    bot.logger.info(f"User {member.name} has roles: {user_roles}")
    bot.logger.info(f"Commissioner roles for server {server_id}: {commissioner_roles}")
    
    if not any(role.name in commissioner_roles for role in member.roles):
        bot.logger.info(f"User {member.name} does not have commissioner permissions")
        return

    channel = guild.get_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    # Handle 🔴 and 🔵 reactions for game results
    if emoji in {"🔴", "🔵"} and record_tracking:
        await _handle_game_result(bot, payload, channel, emoji, server_id, record_tracking)
        return

    # Handle other reactions (✅, 🎲, 🟥, 🟦)
    await _handle_status_reaction(bot, payload, channel, emoji, server_id, record_tracking)

async def _handle_game_result(bot, payload, channel, emoji, server_id, record_tracking):
    """Handle game result reactions (🔴, 🔵)"""
    try:
        msg = await channel.fetch_message(payload.message_id)
        if msg.author.id != bot.user.id:
            return

        content = msg.content.lower()
        if "who won?" not in content:
            return

        parts = strip_status_suffix(channel.name).split("-vs-")
        if len(parts) != 2:
            return

        team1_key = clean_team_key(parts[0])
        team2_key = clean_team_key(parts[1])
        winner_key, loser_key = (team1_key, team2_key) if emoji == "🔴" else (team2_key, team1_key)

        if record_tracking:
            await _record_game_result(server_id, winner_key, loser_key)

        await msg.delete()
        
        # Get updated records
        winner_record, loser_record = await _get_team_records(server_id, winner_key, loser_key, record_tracking)
        
        # Format and send result message
        pretty_winner = format_team_name(winner_key)
        pretty_loser = format_team_name(loser_key)
        
        winner_str = f" ({winner_record[0]}-{winner_record[1]})" if record_tracking else ""
        loser_str = f" ({loser_record[0]}-{loser_record[1]})" if record_tracking else ""

        if record_tracking:
            await channel.send(
                f"📊 Recorded result: **{pretty_winner}**{winner_str} wins over **{pretty_loser}**{loser_str}."
            )

    except Exception as e:
        bot.logger.error(f"[Reaction Record Error] {e}")

async def _handle_status_reaction(bot, payload, channel, emoji, server_id, record_tracking):
    """Handle status reactions (✅, 🎲, 🟥, 🟦)"""
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return

    if message.author.id != bot.user.id:
        return

    original_name = strip_status_suffix(channel.name)
    if "-vs-" not in original_name:
        return

    parts = original_name.split("-vs-")
    if len(parts) != 2:
        return

    # Handle different status reactions
    if emoji in {"✅", "🎲"}:
        await _handle_completion_reaction(bot, payload, channel, emoji, parts, server_id, record_tracking)
    elif emoji == "🟥":
        await _handle_team1_win_reaction(bot, payload, channel, parts, server_id, record_tracking)
    elif emoji == "🟦":
        await _handle_team2_win_reaction(bot, payload, channel, parts, server_id, record_tracking)

async def _handle_completion_reaction(bot, payload, channel, emoji, parts, server_id, record_tracking):
    """Handle completion reactions (✅, 🎲)"""
    new_name = apply_status_suffix(f"{parts[0]}-vs-{parts[1]}", emoji)

    try:
        await channel.edit(name=new_name)
    except discord.Forbidden:
        bot.logger.error(f"Missing permissions to rename channel {channel.name}")
    except Exception as e:
        bot.logger.error(f"Error renaming channel: {e}")

    try:
        # Delete the Game Status Tracker message directly using the message ID from the reaction
        message = await channel.fetch_message(payload.message_id)
        if message.author.id == bot.user.id and "Game Status Tracker" in message.content:
            await message.delete()
        else:
            # Fallback: search for the message if direct deletion fails
            async for msg in channel.history(limit=20):
                if (msg.author.id == bot.user.id and 
                    "Game Status Tracker" in msg.content and
                    any(e in str(msg.content) for e in ["✅", "🎲", "🟥", "🟦"])):
                    await msg.delete()
                    break
    except Exception as e:
        bot.logger.error(f"Error deleting Game Status Tracker message: {e}")

    if record_tracking:
        team1 = parts[0].replace("-", " ").title()
        team2 = parts[1].replace("-", " ").title()
        result_prompt = await channel.send(
            f"{emoji} Game completed. Who won?\nReact:\n🔴 = {team1}\n🔵 = {team2}"
        )
        await result_prompt.add_reaction("🔴")
        await result_prompt.add_reaction("🔵")

async def _handle_team1_win_reaction(bot, payload, channel, parts, server_id, record_tracking):
    """Handle team 1 win reaction (🟥)"""
    new_name = apply_status_suffix(f"fw-{parts[0]}-vs-{parts[1]}", "☑️")
    team1_key = clean_team_key(parts[0])
    team2_key = clean_team_key(parts[1])
    winner_key, loser_key = (team1_key, team2_key)

    if record_tracking:
        await _record_game_result(server_id, winner_key, loser_key)

    await _update_channel_and_cleanup(bot, payload, channel, new_name, server_id, winner_key, loser_key, record_tracking)

async def _handle_team2_win_reaction(bot, payload, channel, parts, server_id, record_tracking):
    """Handle team 2 win reaction (🟦)"""
    new_name = apply_status_suffix(f"{parts[0]}-vs-fw-{parts[1]}", "☑️")
    team1_key = clean_team_key(parts[0])
    team2_key = clean_team_key(parts[1])
    winner_key, loser_key = (team2_key, team1_key)  # 🟦 = Team 2 wins

    if record_tracking:
        await _record_game_result(server_id, winner_key, loser_key)

    await _update_channel_and_cleanup(bot, payload, channel, new_name, server_id, winner_key, loser_key, record_tracking)

async def _record_game_result(server_id, winner_key, loser_key):
    """Record game result in database"""
    with get_db_connection("teams") as conn:
        cursor = conn.cursor()

        # Check if teams are CPU
        cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (winner_key.lower(), server_id))
        winner_row = cursor.fetchone()
        is_winner_cpu = not winner_row or winner_row[0] is None

        cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (loser_key.lower(), server_id))
        loser_row = cursor.fetchone()
        is_loser_cpu = not loser_row or loser_row[0] is None

        if not is_winner_cpu:
            cursor.execute("""
                INSERT INTO cfb_team_records (server_id, team_name, wins, losses)
                VALUES (?, ?, 1, 0)
                ON CONFLICT(server_id, team_name) DO UPDATE SET wins = wins + 1
            """, (server_id, winner_key))

        if not is_loser_cpu:
            cursor.execute("""
                INSERT INTO cfb_team_records (server_id, team_name, wins, losses)
                VALUES (?, ?, 0, 1)
                ON CONFLICT(server_id, team_name) DO UPDATE SET losses = losses + 1
            """, (server_id, loser_key))

        conn.commit()

async def _get_team_records(server_id, winner_key, loser_key, record_tracking):
    """Get team records from database"""
    if not record_tracking:
        return (0, 0), (0, 0)

    with get_db_connection("teams") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wins, losses FROM cfb_team_records
            WHERE server_id = ? AND team_name = ?
        """, (server_id, winner_key))
        winner_record = cursor.fetchone() or (0, 0)

        cursor.execute("""
            SELECT wins, losses FROM cfb_team_records
            WHERE server_id = ? AND team_name = ?
        """, (server_id, loser_key))
        loser_record = cursor.fetchone() or (0, 0)

    return winner_record, loser_record

async def _update_channel_and_cleanup(bot, payload, channel, new_name, server_id, winner_key, loser_key, record_tracking):
    """Update channel name and cleanup messages"""
    try:
        await channel.edit(name=new_name)
    except discord.Forbidden:
        bot.logger.error(f"Missing permissions to rename channel {channel.name}")
    except Exception as e:
        bot.logger.error(f"Error renaming channel: {e}")

    try:
        # Delete the Game Status Tracker message directly using the message ID from the reaction
        message = await channel.fetch_message(payload.message_id)
        if message.author.id == bot.user.id and "Game Status Tracker" in message.content:
            await message.delete()
        else:
            # Fallback: search for the message if direct deletion fails
            async for msg in channel.history(limit=20):
                if (msg.author.id == bot.user.id and 
                    "Game Status Tracker" in msg.content and
                    any(e in str(msg.content) for e in ["✅", "🎲", "🟥", "🟦"])):
                    await msg.delete()
                    break
    except Exception as e:
        bot.logger.error(f"Error deleting Game Status Tracker message: {e}")

    # Get updated records and send result message
    winner_record, loser_record = await _get_team_records(server_id, winner_key, loser_key, record_tracking)
    
    pretty_winner = format_team_name(winner_key)
    pretty_loser = format_team_name(loser_key)
    
    winner_str = f" ({winner_record[0]}-{winner_record[1]})" if record_tracking else ""
    loser_str = f" ({loser_record[0]}-{loser_record[1]})" if record_tracking else ""

    if record_tracking:
        await channel.send(
            f"📊 Recorded result: **{pretty_winner}**{winner_str} wins over **{pretty_loser}**{loser_str}."
        ) 