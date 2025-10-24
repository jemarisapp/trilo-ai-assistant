import discord
from discord import app_commands, ui, ButtonStyle, Interaction
from discord.ext import commands
import sqlite3
from utils.utils import get_db_connection, format_team_name, clean_team_key, format_team_name
from utils.common import commissioner_only, subscription_required, CORE_SKUS
from commands.settings import is_record_tracking_enabled, get_server_setting
from utils.command_logger import log_command


class ConfirmDeleteRecordsView(ui.View):
    def __init__(self, interaction: Interaction, server_id: str, records_table: str):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.server_id = server_id
        self.records_table = records_table

    @ui.button(label="Yes, Clear All", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to confirm this.", ephemeral=True)
            return

        try:
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.records_table} WHERE server_id = ?", (self.server_id,))
                conn.commit()

            await interaction.response.edit_message(
                content="🧹 All team win/loss records have been cleared.",
                view=None
            )
        except Exception as e:
            print(f"[clear_team_records] Error: {e}")
            await interaction.response.edit_message(
                content="⚠️ Failed to clear records.",
                view=None
            )

        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to cancel this.", ephemeral=True)
            return

        await interaction.response.edit_message(content="Cancelled. No records were deleted.", view=None)
        self.stop()

class ConfirmDeleteSingleRecordView(ui.View):
    def __init__(self, interaction: Interaction, server_id: str, team_key: str, display_name: str, records_table: str):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.server_id = server_id
        self.team_key = team_key
        self.display_name = display_name
        self.records_table = records_table

    @ui.button(label="Yes, Clear Record", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to confirm this.", ephemeral=True)
            return

        try:
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.records_table} WHERE server_id = ? AND team_name = ?", (self.server_id, self.team_key))
                conn.commit()

            await interaction.response.edit_message(
                content=f"🧹 Record for **{self.display_name}** has been cleared.",
                view=None
            )
        except Exception as e:
            print(f"[clear_single_team_record] Error: {e}")
            await interaction.response.edit_message(
                content="⚠️ Failed to clear this team's record.",
                view=None
            )

        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to cancel this.", ephemeral=True)
            return

        await interaction.response.edit_message(content="Cancelled. No record was deleted.", view=None)
        self.stop()


def setup_records_commands(bot: commands.Bot):
    records_group = app_commands.Group(name="records", description="Manage records")

    # League resolver and table mapping (defaults to CFB if unset)
    def _resolve_league(interaction: discord.Interaction) -> str:
        server_league = get_server_setting(str(interaction.guild.id), "league_type")
        return (server_league or "cfb").lower()

    def _tables_for_league(interaction: discord.Interaction) -> tuple[str, str]:
        league = _resolve_league(interaction)
        if league == "nfl":
            return "nfl_team_records", "nfl_teams"
        return "cfb_team_records", "cfb_teams"

    
    @subscription_required(allowed_skus=CORE_SKUS)
    @commissioner_only()
    @records_group.command(name="clear-all", description="Clear all win/loss records for this server.")
    @log_command("records clear-all")
    async def clear_team_records(interaction: discord.Interaction):
        
        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return
        
        server_id = str(interaction.guild.id)
        records_table, _ = _tables_for_league(interaction)
        view = ConfirmDeleteRecordsView(interaction, server_id, records_table)

        await interaction.response.send_message(
            "⚠️ Are you sure you want to clear **all** team win/loss records for this server?",
            view=view,
            ephemeral=True
        )


    @subscription_required(allowed_skus=CORE_SKUS)
    @commissioner_only()
    @records_group.command(name="clear-team-record", description="Clear the record for a single team.")
    @app_commands.describe(team_name="The name of the team to reset record for.")
    @log_command("records clear-team-record")
    async def clear_single_team_record(interaction: discord.Interaction, team_name: str):

        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return
        
        server_id = str(interaction.guild.id)
        team_key = clean_team_key(team_name)
        display_name = format_team_name(team_key)

        records_table, _ = _tables_for_league(interaction)
        view = ConfirmDeleteSingleRecordView(interaction, server_id, team_key, display_name, records_table)

        await interaction.response.send_message(
            f"⚠️ Are you sure you want to clear the win/loss record for **{display_name}**?",
            view=view,
            ephemeral=True
        )

    @clear_single_team_record.autocomplete("team_name")
    async def autocomplete_team_name(interaction: discord.Interaction, current: str):
        server_id = str(interaction.guild.id)
        records_table, _ = _tables_for_league(interaction)
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT DISTINCT team_name FROM {records_table}
                WHERE server_id = ? AND team_name LIKE ?
                ORDER BY team_name ASC
                LIMIT 10
            """, (server_id, f"{current.lower()}%"))
            results = cursor.fetchall()

        return [
            discord.app_commands.Choice(name=team.replace("-", " ").title(), value=team)
            for team, in results
        ]
    
    @subscription_required(allowed_skus=CORE_SKUS)
    @commissioner_only()
    @records_group.command(name="check-record", description="Check the win/loss record of a team.")
    @app_commands.describe(team_name="Select the team to check.")
    @log_command("records check-record")
    async def check_team_record(interaction: discord.Interaction, team_name: str):
    
        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return

        server_id = str(interaction.guild.id)
        team_key = clean_team_key(team_name)
        pretty_name = format_team_name(team_key)

        records_table, _ = _tables_for_league(interaction)
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT wins, losses FROM {records_table}
                WHERE server_id = ? AND team_name = ?
            """, (server_id, team_key))
            record = cursor.fetchone()

        if record:
            wins, losses = record
            await interaction.response.send_message(f"📊 **{pretty_name}**: {wins} Wins – {losses} Losses", ephemeral=True)
        else:
            await interaction.response.send_message(f"📊 **{pretty_name}** has no recorded games yet.", ephemeral=True)
            
    @check_team_record.autocomplete("team_name")
    async def autocomplete_team_name(interaction: discord.Interaction, current: str):
        server_id = str(interaction.guild.id)
        records_table, _ = _tables_for_league(interaction)
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT DISTINCT team_name FROM {records_table}
                WHERE server_id = ? AND team_name LIKE ?
                ORDER BY team_name ASC
                LIMIT 10
            """, (server_id, f"{current.lower()}%"))
            results = cursor.fetchall()

        return [
            discord.app_commands.Choice(name=team.replace("-", " ").title(), value=team)
            for team, in results
        ]

    @subscription_required(allowed_skus=CORE_SKUS)
    @commissioner_only()
    @records_group.command(name="view-all-records", description="View all team win/loss records for this server.")
    @log_command("records view-all-records")
    async def view_team_standings(interaction: discord.Interaction):
        
        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return

        server_id = str(interaction.guild.id)

        records_table, teams_table = _tables_for_league(interaction)
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT r.team_name, r.wins, r.losses
                FROM {records_table} r
                JOIN {teams_table} t ON r.server_id = t.server_id AND r.team_name = t.team_name
                WHERE r.server_id = ?
            """, (server_id,))
            rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message("📭 No win/loss records found for this server.", ephemeral=True)
            return

        # Calculate win % and sort
        records = []
        for team, wins, losses in rows:
            games = wins + losses
            win_pct = wins / games if games > 0 else 0
            records.append((team, wins, losses, win_pct))

        records.sort(key=lambda x: (-x[3], -x[1]))  # Sort by win%, then wins

        # Format standings
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (team, wins, losses, win_pct) in enumerate(records[:32], start=1):
            pretty_team = format_team_name(team)

            # Try to find the user assigned to this team
            cursor.execute(f"""
                SELECT user_id FROM {teams_table}
                WHERE server_id = ? AND team_name = ?
            """, (server_id, team))
            owner_row = cursor.fetchone()
            user_tag = f"<@{owner_row[0]}>" if owner_row else "CPU"

            prefix = medals[i-1] if i <= 3 else f"{i}."
            lines.append(f"**{prefix} {user_tag} — {pretty_team} — {wins}-{losses}**")



        embed = discord.Embed(
            title="🏆 Team Records",
            description="\n".join(lines[:32]),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @subscription_required(allowed_skus=CORE_SKUS)
    @commissioner_only()
    @records_group.command(name="set-record", description="Manually set the win/loss record for a user-assigned team.")
    @app_commands.describe(
        user="Select the user whose team record to update",
        wins="Number of wins",
        losses="Number of losses"
    )
    @log_command("records set-record")
    async def set_team_record(
        interaction: discord.Interaction,
        user: discord.Member,
        wins: int,
        losses: int
    ):

        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return
        
        server_id = str(interaction.guild.id)

        # Lookup team for the user
        _, teams_table = _tables_for_league(interaction)
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT team_name FROM {teams_table}
                WHERE server_id = ? AND user_id = ?
            """, (server_id, user.id))
            result = cursor.fetchone()

        if not result:
            await interaction.response.send_message(f"❌ {user.mention} does not have a team assigned.", ephemeral=True)
            return

        team_key = clean_team_key(result[0])
        pretty_name = format_team_name(team_key)

        try:
            records_table, _ = _tables_for_league(interaction)
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    INSERT INTO {records_table} (server_id, team_name, wins, losses, last_updated)
                    VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                    ON CONFLICT(server_id, team_name)
                    DO UPDATE SET wins = excluded.wins, losses = excluded.losses, last_updated = datetime('now', 'localtime')
                """, (server_id, team_key, wins, losses))
                conn.commit()

            await interaction.response.send_message(
                f"✅ Record for **{pretty_name}** ({user.mention}) set to **{wins}-{losses}**.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[set_team_record] Error: {e}")
            await interaction.response.send_message("⚠️ Failed to set record.", ephemeral=True)



    # Overview command removed - use /help feature records instead

    bot.tree.add_command(records_group)
