# File: commands/teams.py
import discord
from discord import app_commands, ui, ButtonStyle, Interaction
from discord.ext import commands
import sqlite3
from utils.utils import get_db_connection, format_team_name, clean_team_key, format_team_name
from utils.common import commissioner_only, subscription_required, ALL_PREMIUM_SKUS
from commands.settings import is_record_tracking_enabled, get_server_setting
from utils.command_logger import log_command


def setup_team_commands(bot: commands.Bot):
    teams_group = app_commands.Group(name="teams", description="Manage team assignments")

    # ─────────────────────────────────────────────────────────────
    # League resolver and table mapping (defaults to CFB if unset)
    # ─────────────────────────────────────────────────────────────
    def _resolve_league(interaction: discord.Interaction) -> str:
        server_league = get_server_setting(str(interaction.guild.id), "league_type")
        return (server_league or "cfb").lower()

    def _tables_for_league(interaction: discord.Interaction) -> tuple[str, str]:
        league = _resolve_league(interaction)
        if league == "nfl":
            return "nfl_teams", "nfl_valid_teams"
        return "cfb_teams", "cfb_valid_teams"

    # ─────────────────────────────────────────────────────────────
    # Unified commands (default to server league_type, fallback CFB)
    # ─────────────────────────────────────────────────────────────
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @teams_group.command(name="assign-user", description="Assign a user to a team (CFB/NFL based on server setting)")
    @app_commands.describe(user="The user to assign.", team_name="The team to assign the user to.")
    @log_command("teams assign-user")
    async def assign_user_to_team_unified(interaction: discord.Interaction, user: discord.Member, team_name: str):
        conn = None
        try:
            # Validate team_name via autocomplete
            conn = get_db_connection("teams")
            cursor = conn.cursor()
            teams_table, valid_table = _tables_for_league(interaction)

            # Convert team_name to lowercase for uniformity
            team_name_lower = team_name.lower()

            # Check if the team_name exists in the valid teams table
            cursor.execute(f"SELECT 1 FROM {valid_table} WHERE team_name = ?", (team_name_lower,))
            if not cursor.fetchone():
                await interaction.response.send_message(f"'{team_name}' is not a valid team. Please choose a valid team.", ephemeral=True)
                return

            # Check if the team is already assigned to another user
            cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team_name_lower, str(interaction.guild.id)))
            existing_assignment = cursor.fetchone()

            if existing_assignment:
                # If the team is already assigned to a user, notify the commissioner
                assigned_user_id = existing_assignment[0]
                try:
                    assigned_user = await interaction.guild.fetch_member(assigned_user_id)
                    await interaction.response.send_message(f"'{team_name}' is already assigned to {assigned_user.mention}. Please choose another team.", ephemeral=True)
                except discord.NotFound:
                    # User no longer exists, remove the assignment and continue
                    cursor.execute(f"DELETE FROM {teams_table} WHERE user_id = ? AND server_id = ?", (assigned_user_id, str(interaction.guild.id)))
                    conn.commit()
                else:
                    return

            # Proceed with assigning the user to the team after validation
            server_id = str(interaction.guild.id)  # Get the server ID

            # Check if the user is already assigned to a team in this server
            cursor.execute(f"SELECT team_name FROM {teams_table} WHERE user_id = ? AND server_id = ?", (user.id, server_id))
            existing_team = cursor.fetchone()

            # Prepare the response message
            if existing_team:
                old_team = existing_team[0]  # Retrieve the old team name from the result
                # Remove the previous team assignment if the user is already assigned to a team
                cursor.execute(f"DELETE FROM {teams_table} WHERE user_id = ? AND server_id = ?", (user.id, server_id))
                conn.commit()
                response_message = f"{user.mention} has been removed from '{old_team}' and assigned to '{team_name_lower}'."
            else:
                # If the user was not previously assigned to a team, notify about the new assignment
                response_message = f"{user.mention} has been assigned to '{team_name_lower}' in this server."
            
            # Now assign the user to the new team
            cursor.execute(
                f"INSERT INTO {teams_table} (team_name, user_id, server_id, created_at, updated_at) VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))",
                (team_name_lower, user.id, server_id)
            )
            conn.commit()
            
            # Send response after all database operations are complete
            await interaction.response.send_message(response_message)
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error in assign_user_to_team: {e}")
            await interaction.response.send_message("An error occurred while assigning the team. Please try again.", ephemeral=True)
        finally:
            if conn:
                conn.close()

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @teams_group.command(name="unassign-user", description="Unassign a user from their current team (CFB/NFL)")
    @app_commands.describe(user="The user to unassign from their team.")
    @log_command("teams unassign-user")
    async def unassign_user_unified(interaction: discord.Interaction, user: discord.Member):

        server_id = str(interaction.guild.id)

        conn = get_db_connection("teams")
        cursor = conn.cursor()
        teams_table, _ = _tables_for_league(interaction)

        # Check if the user has a team
        cursor.execute(f"SELECT team_name FROM {teams_table} WHERE user_id = ? AND server_id = ?", (user.id, server_id))
        result = cursor.fetchone()

        if result:
            team_name = result[0]
            cursor.execute(f"DELETE FROM {teams_table} WHERE user_id = ? AND server_id = ?", (user.id, server_id))
            conn.commit()
            await interaction.response.send_message(f"{user.mention} has been unassigned from **{format_team_name(team_name)}**.")
        else:
            await interaction.response.send_message(f"{user.mention} is not assigned to any team in this server.", ephemeral=True)

        conn.close()


    # Command: remove-team-assignment
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @teams_group.command(name="clear-team", description="Remove a team's current user assignment in this server")
    @app_commands.describe(team_name="The team to remove.")
    @log_command("teams clear-team")
    async def clear_team_unified(interaction: discord.Interaction, team_name: str):
        
        """Remove a team's user assignment within the server."""
        conn = get_db_connection("teams")
        cursor = conn.cursor()

        server_id = str(interaction.guild.id)  # Get the server ID
        team_name = team_name.lower()
        teams_table, _ = _tables_for_league(interaction)

        # Check if the team exists in this server
        cursor.execute(f"SELECT 1 FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team_name, server_id))
        if cursor.fetchone():
            cursor.execute(f"DELETE FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team_name, server_id))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"Team '{team_name}' has been removed from this server.")
        else:
            conn.close()
            await interaction.response.send_message(f"Team '{team_name}' is not assigned to anyone in this server.")

    # Adding autocomplete limit for ASSIGN team_name
    @assign_user_to_team_unified.autocomplete("team_name")
    async def team_name_autocomplete_unified(interaction: discord.Interaction, current: str):
        conn = get_db_connection("teams")
        cursor = conn.cursor()
        _, valid_table = _tables_for_league(interaction)
        # Fetch team names from valid table with a limit of 10
        cursor.execute(f"SELECT team_name FROM {valid_table} WHERE team_name LIKE ? LIMIT 10", (f"{current.lower()}%",))
        teams = cursor.fetchall()

        # Send suggestions for autocomplete
        suggestions = [team[0] for team in teams]
        await interaction.response.autocomplete(choices=[
            discord.app_commands.Choice(name=team, value=team) for team in suggestions
        ])

        conn.close()

    # who-has (unified)
    @teams_group.command(name="who-has", description="Check which user is assigned to a specific team (CFB/NFL)")
    @app_commands.describe(team_name="The team to check.")
    @log_command("teams who-has")
    async def who_has_team_unified(interaction: discord.Interaction, team_name: str):
        conn = get_db_connection("teams")
        cursor = conn.cursor()
        server_id = str(interaction.guild.id)
        team_key = team_name.lower()
        teams_table, _ = _tables_for_league(interaction)
        cursor.execute(
            f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?",
            (team_key, server_id)
        )
        user = cursor.fetchone()
        conn.close()
        pretty_team = format_team_name(team_key)
        if user:
            await interaction.response.send_message(f"**{pretty_team}** is assigned to <@{user[0]}>.", ephemeral=False)
        else:
            await interaction.response.send_message(f"**{pretty_team}** is not assigned to anyone (CPU).", ephemeral=False)

    @who_has_team_unified.autocomplete("team_name")
    async def who_has_team_autocomplete_unified(interaction: discord.Interaction, current: str):
        conn = get_db_connection("teams")
        cursor = conn.cursor()
        server_id = str(interaction.guild.id)
        teams_table, _ = _tables_for_league(interaction)
        cursor.execute(
            f"SELECT DISTINCT team_name FROM {teams_table} WHERE server_id = ? AND team_name LIKE ? LIMIT 10",
            (server_id, f"{current.lower()}%")
        )
        teams = cursor.fetchall()
        conn.close()
        suggestions = [team[0] for team in teams]
        await interaction.response.autocomplete(choices=[
            discord.app_commands.Choice(name=format_team_name(team), value=team) for team in suggestions
        ])

    # Adding autocomplete for limit REMOVE team_name
    @clear_team_unified.autocomplete("team_name")
    async def clear_team_autocomplete_unified(interaction: discord.Interaction, current: str):
        conn = get_db_connection("teams")
        cursor = conn.cursor()

        # Fetch team names assigned within the server, limiting to 10 results
        server_id = str(interaction.guild.id)
        teams_table, _ = _tables_for_league(interaction)
        cursor.execute(
            f"SELECT team_name FROM {teams_table} WHERE server_id = ? AND team_name LIKE ? LIMIT 10", 
            (server_id, f"{current.lower()}%")
        )
        teams = cursor.fetchall()

        # Send suggestions for autocomplete
        suggestions = [team[0] for team in teams]
        await interaction.response.autocomplete(choices=[
            discord.app_commands.Choice(name=team, value=team) for team in suggestions
        ])

        conn.close()

    # (All separate NFL clear-team and related autocompletes removed in favor of unified commands)

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @teams_group.command(name="list-all", description="List all users assigned to teams (CFB/NFL)")
    @log_command("teams list-all")
    async def list_all_assignments_unified(interaction: discord.Interaction):

        server_id = str(interaction.guild.id)

        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            teams_table, _ = _tables_for_league(interaction)
            cursor.execute(f"SELECT user_id, team_name FROM {teams_table} WHERE server_id = ?", (server_id,))
            assignments = cursor.fetchall()

        if not assignments:
            await interaction.response.send_message("No users have been assigned to teams in this server.", ephemeral=False, silent=True)
            return

        # Build all lines with actual user mentions
        lines = []
        for user_id, team_name in assignments:
            lines.append(f"<@{user_id}> → **{format_team_name(team_name)}**")

        # Join all lines into a single message
        message_content = f"📋 **Team Assignments ({len(assignments)} total)**\n\n" + "\n".join(lines)
        
        # Split into chunks if message is too long (Discord limit is 2000 chars)
        if len(message_content) > 2000:
            chunks = []
            current_chunk = f"📋 **Team Assignments ({len(assignments)} total)**\n\n"
            
            for line in lines:
                if len(current_chunk) + len(line) > 1900:  # Leave some buffer
                    chunks.append(current_chunk)
                    current_chunk = f"📋 **Team Assignments (continued)**\n\n"
                current_chunk += line + "\n"
            
            if current_chunk:
                chunks.append(current_chunk)
            
            for chunk in chunks:
                await interaction.followup.send(chunk, ephemeral=False, silent=True)
        else:
            await interaction.response.send_message(message_content, ephemeral=False, silent=True)

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    # (Deprecated specific list-all commands kept below; unified version above)



    # Command: remove-all-assignments
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @teams_group.command(name="clear-all-assignments", description="Remove all team assignments from this server (CFB/NFL)")
    @log_command("teams clear-all-assignments")
    async def remove_all_assignments_unified(interaction: discord.Interaction):

        server_id = str(interaction.guild.id)  # Get the server ID

        try:
            connection = get_db_connection("teams")
            cursor = connection.cursor()
            teams_table, _ = _tables_for_league(interaction)
            cursor.execute(f"DELETE FROM {teams_table} WHERE server_id = ?", (server_id,))
            connection.commit()

            # Send a response to confirm the action
            await interaction.response.send_message(f"All team assignments have been removed in this server.")
            connection.close()  # Close the connection

        except Exception as e:
            print(f"Error removing all CFB team assignments: {e}")
            await interaction.response.send_message("An error occurred while removing the CFB team assignments.")

    # (Removed separate NFL clear-all-assignments; unified command handles both)


    # (Removed separate CFB/NFL who-has; unified who-has provided above)
    
    # Overview command removed - use /help feature teams instead
    
    bot.tree.add_command(teams_group)
