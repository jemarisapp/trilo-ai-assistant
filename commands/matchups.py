# File: commands/matchups.py
import discord
import logging
from discord.ext import commands
from discord import app_commands, ui
from discord import ui, Interaction, ButtonStyle
import asyncio
from typing import Literal
from utils.utils import get_db_connection, clean_team_key, strip_status_suffix, apply_status_suffix, format_team_name
from utils.common import commissioner_only, subscription_required, ALL_PREMIUM_SKUS
from commands.settings import is_record_tracking_enabled, get_server_setting, is_matchup_auto_confirm_enabled
from utils.command_logger import log_command
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import requests
from typing import List, Tuple, Optional
import openai
from openai import OpenAI
import re

# Just read the env var already loaded in main.py
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("❌ No OpenAI API Key found. Make sure it's in secrets.env and loaded in main.py.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Module-level league table resolver for contexts without an Interaction
def _tables_for_guild_id(guild_id: str) -> tuple[str, str]:
    """Return (teams_table, records_table) based on server setting for a guild id."""
    server_league = get_server_setting(str(guild_id), "league_type")
    if (server_league or "cfb").lower() == "nfl":
        return "nfl_teams", "nfl_team_records"
    return "cfb_teams", "cfb_team_records"

async def process_matchup_image(image_url: str) -> Tuple[Optional[str], List[str]]:
    """
    Process an uploaded image to extract matchup information using OpenAI Vision API
    
    Returns:
        Tuple of (category_name, list_of_matchups)
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        payload = {
            "model": "gpt-4o",  # or gpt-4o-mini for cheaper option
            "messages": [
            {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract matchup information from this image.

OUTPUT
- Return only the lines under MATCHUPS in the form: Team1 vs Team2
- One matchup per line. No numbering or extra text.

CATEGORY
- Derive a category like Week N / Playoffs / Bowl Games / Championship when present.
- Use the most prominent identifier. If none is visible, use a generic label like Matchups.

MATCHUP PARSING
- The left side is the first team (away) and the right side is the second team (home). Treat AT/@ or column layout as away→home.
- Ignore scores, records, dates, and UI.
- Use the separator exactly: " vs " (space-vs-space).

COLLEGE (CFB) NAMES
- Keep the school/team wording visible in the image (city or school name is fine).
- Remove rankings or seed numbers (e.g., 24 Florida vs 1 Alabama → Florida vs Alabama).

NFL NAMES (when the image is clearly NFL)
- Convert any city/abbr/logo to the canonical nickname only (no city):
  Bills, Dolphins, Patriots, Jets, Ravens, Bengals, Browns, Steelers, Texans, Colts,
  Jaguars, Titans, Broncos, Chiefs, Raiders, Chargers, Cowboys, Giants, Eagles, Commanders,
  Bears, Lions, Packers, Vikings, Falcons, Panthers, Saints, Buccaneers, Cardinals, Rams, 49ers, Seahawks
- Keep exact casing/spelling above (e.g., 49ers as digits).

ORDER & DEDUP
- Read top→bottom in the left column, then top→bottom in the right column.
- If a matchup repeats, include it only once.

FORMAT
Return exactly:
CATEGORY: [category name]
MATCHUPS:
Team1 vs Team2
Team3 vs Team4
... (one per line)

If a row is incomplete or unreadable, skip it rather than guessing."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1  # Low temperature for more consistent extraction
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", 
                               headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"OpenAI API error: {response.status_code} - {response.text}")
            return None, []
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Parse the response
        lines = content.strip().split('\n')
        category_name = None
        matchups = []
        
        in_matchups_section = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("CATEGORY:"):
                category_name = line.replace("CATEGORY:", "").strip()
            elif line == "MATCHUPS:":
                in_matchups_section = True
            elif in_matchups_section and line and " vs " in line:
                matchups.append(line)
        
        return category_name, matchups
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return None, []




class WinnerButtonsView(ui.View):
    def __init__(self, guild_id, team1, team2, channel_name):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.team1 = team1
        self.team2 = team2
        self.channel_name = channel_name

        # Create buttons manually with dynamic labels
        button1 = ui.Button(label=f"{team1.title()} Won", style=ButtonStyle.danger)
        button2 = ui.Button(label=f"{team2.title()} Won", style=ButtonStyle.primary)

        button1.callback = self.make_callback(team1, team2)
        button2.callback = self.make_callback(team2, team1)

        self.add_item(button1)
        self.add_item(button2)

    def make_callback(self, winner: str, loser: str):
        async def callback(interaction: Interaction):
            try:
                with get_db_connection("teams") as conn:
                    cursor = conn.cursor()
                    teams_table, records_table = _tables_for_guild_id(self.guild_id)
                    # Check if winner or loser is CPU (not assigned to a user)
                    cursor.execute(
                        f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?",
                        (winner.lower(), str(self.guild_id))
                    )
                    winner_user = cursor.fetchone()

                    cursor.execute(
                        f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?",
                        (loser.lower(), str(self.guild_id))
                    )
                    loser_user = cursor.fetchone()

                    # Only log records for user-controlled teams
                    if winner_user:
                        cursor.execute(f"""
                            INSERT INTO {records_table} (server_id, team_name, wins, losses)
                            VALUES (?, ?, 1, 0)
                            ON CONFLICT(server_id, team_name) DO UPDATE SET wins = wins + 1
                        """, (str(self.guild_id), winner))

                    if loser_user:
                        cursor.execute(f"""
                            INSERT INTO {records_table} (server_id, team_name, wins, losses)
                            VALUES (?, ?, 0, 1)
                            ON CONFLICT(server_id, team_name) DO UPDATE SET losses = losses + 1
                        """, (str(self.guild_id), loser))

                    conn.commit()

                server_id = str(self.guild_id)

                with get_db_connection("teams") as conn:
                    cursor = conn.cursor()
                    teams_table, records_table = _tables_for_guild_id(server_id)
                    # Re-check user control status
                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (winner.lower(), server_id))
                    winner_user = cursor.fetchone()
                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (loser.lower(), server_id))
                    loser_user = cursor.fetchone()

                    # Build display name for winner
                    winner_display = winner.title()
                    if winner_user:
                        cursor.execute(f"SELECT wins, losses FROM {records_table} WHERE server_id = ? AND team_name = ?", (server_id, winner.lower()))
                        rec = cursor.fetchone()
                        if rec:
                            winner_display += f" ({rec[0]}-{rec[1]})"
                    else:
                        winner_display += " (CPU)"

                    # Build display name for loser
                    loser_display = loser.title()
                    if loser_user:
                        cursor.execute(f"SELECT wins, losses FROM {records_table} WHERE server_id = ? AND team_name = ?", (server_id, loser.lower()))
                        rec = cursor.fetchone()
                        if rec:
                            loser_display += f" ({rec[0]}-{rec[1]})"
                    else:
                        loser_display += " (CPU)"

                await interaction.response.edit_message(
                    content=f"📊 Recorded result: **{winner_display}** wins over **{loser_display}**.",
                    view=None
                )

                
            except Exception as e:
                print(f"[WinnerButtonsView] DB update failed: {e}")
                await interaction.response.edit_message(content="⚠️ Failed to update records.", view=None)

        return callback


class ShowRecordsEditPromptView(ui.View):
    def __init__(self, interaction: discord.Interaction, created_messages):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.created_messages = created_messages  # List of (channel, message, team1_key, team2_key)

    @ui.button(label="✅ Show Records", style=ButtonStyle.success)
    async def show(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You aren't authorized to do this.", ephemeral=True)
            return

        # Acknowledge the interaction immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        server_id = str(interaction.guild.id)
        updated_count = 0
        error_count = 0

        for channel, msg, team1_key, team2_key in self.created_messages:
            try:
                with get_db_connection("teams") as conn:
                    cursor = conn.cursor()

                    def get_record(team_key):
                        cursor.execute("""
                            SELECT wins, losses FROM cfb_team_records
                            WHERE server_id = ? AND team_name = ?
                        """, (server_id, team_key))
                        return cursor.fetchone() or (0, 0)

                    rec1 = get_record(team1_key)
                    rec2 = get_record(team2_key)
                    
                    cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), server_id))
                    user1 = cursor.fetchone()
                    cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), server_id))
                    user2 = cursor.fetchone()
                    team1_cpu = user1 is None
                    team2_cpu = user2 is None

                pretty_team1 = format_team_name(team1_key)
                pretty_team2 = format_team_name(team2_key)

                content = (
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1} {'(CPU)' if team1_cpu else f'({rec1[0]}-{rec1[1]})'}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2} {'(CPU)' if team2_cpu else f'({rec2[0]}-{rec2[1]})'}**\n\n"
                    "*Records current as of matchup creation — may not reflect live records*"
                )

                await msg.edit(content=content)
                updated_count += 1
                
            except discord.NotFound:
                print(f"[Edit Warning] Message in {channel.name} was deleted before it could be updated.")
                error_count += 1
            except Exception as e:
                print(f"[Edit Error] Failed to update message in {channel.name}: {e}")
                error_count += 1

        # Send the final response
        if error_count == 0:
            await interaction.followup.send("✅ Records have been added to all matchup messages.", ephemeral=True)
        elif updated_count > 0:
            await interaction.followup.send(f"✅ Records added to {updated_count} matchup messages. {error_count} messages could not be updated.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to update any matchup messages. Please try again.", ephemeral=True)
        
        self.stop()
class ShowRecordsEditPromptViewUnified(ui.View):
    def __init__(self, interaction: discord.Interaction, created_messages):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.created_messages = created_messages

    @ui.button(label="✅ Show Records", style=ButtonStyle.success)
    async def show(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You aren't authorized to do this.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        server_id = str(interaction.guild.id)
        teams_table, records_table = _tables_for_guild_id(server_id)
        updated_count = 0
        error_count = 0

        for channel, msg, team1_key, team2_key in self.created_messages:
            try:
                with get_db_connection("teams") as conn:
                    cursor = conn.cursor()

                    def get_record(team_key):
                        cursor.execute(
                            f"SELECT wins, losses FROM {records_table} WHERE server_id = ? AND team_name = ?",
                            (server_id, team_key)
                        )
                        return cursor.fetchone() or (0, 0)

                    rec1 = get_record(team1_key)
                    rec2 = get_record(team2_key)

                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), server_id))
                    user1 = cursor.fetchone()
                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), server_id))
                    user2 = cursor.fetchone()
                    team1_cpu = user1 is None
                    team2_cpu = user2 is None

                pretty_team1 = format_team_name(team1_key)
                pretty_team2 = format_team_name(team2_key)

                content = (
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1} {'(CPU)' if team1_cpu else f'({rec1[0]}-{rec1[1]})'}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2} {'(CPU)' if team2_cpu else f'({rec2[0]}-{rec2[1]})'}**\n\n"
                    "*Records current as of matchup creation — may not reflect live records*"
                )

                await msg.edit(content=content)
                updated_count += 1
            except discord.NotFound:
                error_count += 1
            except Exception:
                error_count += 1

        if error_count == 0:
            await interaction.followup.send("✅ Records have been added to all matchup messages.", ephemeral=True)
        elif updated_count > 0:
            await interaction.followup.send(f"✅ Records added to {updated_count} matchup messages. {error_count} messages could not be updated.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to update any matchup messages. Please try again.", ephemeral=True)

        self.stop()

    @ui.button(label="❌ Skip", style=ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You aren't authorized to do this.", ephemeral=True)
            return
        await interaction.response.send_message("No changes were made to matchup messages.", ephemeral=True)
        self.stop()


def prettify_team(name):
    name = name.strip()

    # Handle specific replacements first
    fixed_cases = {
        "texas a&m": "Texas A&M",
        "fcs school": "FCS School"
    }

    key = name.lower()
    if key in fixed_cases:
        return fixed_cases[key]

    # Capitalize acronyms
    acronyms = {"usc", "lsu", "ucla", "fiu", "fau", "smu", "byu", "tcu", "unlv", "utsa", "uab", "usf", "ucf", "umass", "uconn"}
    return " ".join([w.upper() if w.lower() in acronyms else w.capitalize() for w in name.split()])

def determine_best_category_name(category_names):
    """
    Determine the best category name from multiple extracted category names.
    Prioritizes consistency and common patterns.
    """
    if not category_names:
        return "Multi-Image Matchups"
    
    if len(category_names) == 1:
        return category_names[0]
    
    # Remove None/empty values
    valid_names = [name for name in category_names if name and name.strip()]
    if not valid_names:
        return "Multi-Image Matchups"
    
    # If all names are the same, use that name
    if len(set(valid_names)) == 1:
        return valid_names[0]
    
    # Look for common patterns
    week_pattern = re.compile(r'week\s+(\d+)', re.IGNORECASE)
    playoff_pattern = re.compile(r'playoff|championship|final', re.IGNORECASE)
    
    # Check if all are weeks - if so, find the range or most common
    week_numbers = []
    for name in valid_names:
        match = week_pattern.search(name)
        if match:
            week_numbers.append(int(match.group(1)))
    
    if len(week_numbers) == len(valid_names):
        # All are weeks
        if len(set(week_numbers)) == 1:
            # Same week number
            return f"Week {week_numbers[0]}"
        else:
            # Multiple weeks - use range or most common
            min_week = min(week_numbers)
            max_week = max(week_numbers)
            if max_week - min_week <= 2:  # Close weeks, show range
                return f"Weeks {min_week}-{max_week}"
            else:
                # Use most common week
                from collections import Counter
                most_common = Counter(week_numbers).most_common(1)[0][0]
                return f"Week {most_common}"
    
    # Check if all are playoff-related
    playoff_names = [name for name in valid_names if playoff_pattern.search(name)]
    if len(playoff_names) == len(valid_names):
        # All playoff-related, use the first one or most descriptive
        longest = max(playoff_names, key=len)
        return longest
    
    # Mixed categories - use the most common or first valid one
    from collections import Counter
    name_counts = Counter(valid_names)
    most_common = name_counts.most_common(1)[0][0]
    
    return most_common


def setup_matchup_commands(bot: commands.Bot):
    matchups_group = app_commands.Group(name="matchups", description="Manage matchup channels")
    
    # League resolver and table mapping (defaults to CFB if unset)
    def _resolve_league(interaction: discord.Interaction) -> str:
        server_league = get_server_setting(str(interaction.guild.id), "league_type")
        return (server_league or "cfb").lower()
    
    def _tables_for_league(interaction: discord.Interaction) -> tuple[str, str, str]:
        league = _resolve_league(interaction)
        if league == "nfl":
            return "nfl_teams", "nfl_team_records", "nfl-matchups"
        return "cfb_teams", "cfb_team_records", "cfb-matchups"

    def _tables_for_guild_id(guild_id: str) -> tuple[str, str]:
        """Return (teams_table, records_table) for a given guild id based on server setting."""
        server_league = get_server_setting(str(guild_id), "league_type")
        if (server_league or "cfb").lower() == "nfl":
            return "nfl_teams", "nfl_team_records"
        return "cfb_teams", "cfb_team_records"
    
    # New command to add to your matchups_group (CFB)
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="create-from-image", description="Create matchups by uploading images of schedules (up to 5 images)")
    @app_commands.describe(
        category_name="Type a new category name or choose a pre-existing one.",
        image1="Upload first image containing matchup information (required)",
        image2="Upload second image (optional)",
        image3="Upload third image (optional)",
        image4="Upload fourth image (optional)",
        image5="Upload fifth image (optional)",
        game_status="Set this to True to show outcome tracking reactions in each matchup",
        roles_allowed="Choose roles allowed to view the category (optional)"
    )
    @log_command("matchups create-from-image")
    async def create_matchups_from_image(
        interaction: discord.Interaction,
        category_name: str,
        image1: discord.Attachment,
        image2: discord.Attachment = None,
        image3: discord.Attachment = None,
        image4: discord.Attachment = None,
        image5: discord.Attachment = None,
        game_status: bool = False,
        roles_allowed: str = ""
    ):
        """Create matchup channels from uploaded images"""
        
        # Collect all provided images
        images = [img for img in [image1, image2, image3, image4, image5] if img is not None]
        
        # Validate all images
        for i, image in enumerate(images, 1):
            if not image.content_type or not image.content_type.startswith('image/'):
                await interaction.response.send_message(f"❌ Image {i} is not a valid image file.", ephemeral=True)
                return
            
            if image.size > 10 * 1024 * 1024:  # 10MB limit
                await interaction.response.send_message(f"❌ Image {i} is too large. Please use images under 10MB.", ephemeral=True)
                return
        
        await interaction.response.defer(thinking=True)
        
        try:
            resolved_league = _resolve_league(interaction)
            all_matchups = []
            all_categories = []
            
            # Process each image
            for i, image in enumerate(images, 1):
                try:
                    extracted_category, matchups = await process_matchup_image(image.url)
                    
                    if extracted_category and matchups:
                        all_categories.append(f"Image {i}: {extracted_category}")
                        all_matchups.extend(matchups)
                    else:
                        try:
                            await interaction.followup.send(
                                f"⚠️ Could not extract matchup information from image {i}. Skipping this image.", 
                                ephemeral=True
                            )
                        except Exception as send_error:
                            # If we can't send the message, just log it and continue
                            print(f"Could not send followup message for image {i}: {send_error}")
                except Exception as img_error:
                    print(f"Error processing image {i}: {img_error}")
                    try:
                        await interaction.followup.send(
                            f"⚠️ Error processing image {i}. Skipping this image.", 
                            ephemeral=True
                        )
                    except:
                        pass
            
            if not all_matchups:
                await interaction.followup.send(
                    "❌ Could not extract matchup information from any of the images. Please make sure the images clearly show team matchups.", 
                    ephemeral=True
                )
                return
            
            # Use the user-provided category name instead of extracted one
            final_category = category_name
            
            # Check for CPU vs CPU games that will be skipped
            cpu_vs_cpu_count = 0
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                for matchup in all_matchups:
                    team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                            matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))
                    team1_key = clean_team_key(team1_raw.strip())
                    team2_key = clean_team_key(team2_raw.strip())
                    
                    teams_table, _, _ = _tables_for_league(interaction)
                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), str(interaction.guild.id)))
                    user1 = cursor.fetchone()
                    cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), str(interaction.guild.id)))
                    user2 = cursor.fetchone()
                    
                    if user1 is None and user2 is None:
                        cpu_vs_cpu_count += 1

            # Show preview and ask for confirmation
            preview_embed = discord.Embed(
                title="🔍 Extracted Matchup Information",
                description=f"**Category:** {final_category}\n\n**Found {len(all_matchups)} total matchups from {len(images)} image(s):**",
                color=discord.Color.blue()
            )
            
            matchup_list = "\n".join([f"• {matchup}" for matchup in all_matchups[:20]])  # Limit display
            if len(all_matchups) > 20:
                matchup_list += f"\n... and {len(all_matchups) - 20} more"
            
            preview_embed.add_field(
                name="Matchups",
                value=matchup_list,
                inline=False
            )
            
            if cpu_vs_cpu_count > 0:
                preview_embed.add_field(
                    name="🤖 CPU vs CPU Games",
                    value=f"{cpu_vs_cpu_count} CPU vs CPU games will be automatically skipped (no channels created)",
                    inline=False
                )
            
            if len(all_categories) > 1:
                preview_embed.add_field(
                    name="📸 Processed Images",
                    value="\n".join(all_categories),
                    inline=False
                )
            
            class ConfirmImageMatchupsView(ui.View):
                def __init__(self, original_user):
                    super().__init__(timeout=60)
                    self.confirmed = False
                    self.original_user = original_user
                
                @ui.button(label="✅ Create These Matchups", style=ButtonStyle.success)
                async def confirm(self, interaction: discord.Interaction, button: ui.Button):
                    # Store the original user who created the view
                    original_user = self.original_user if hasattr(self, 'original_user') else None
                    if original_user and interaction.user.id != original_user.id:
                        await interaction.response.send_message("Only the original user can confirm this.", ephemeral=True)
                        return
                    
                    self.confirmed = True
                    await interaction.response.edit_message(
                        content="Creating matchups...", 
                        embed=None, 
                        view=None
                    )
                    
                    # Now create the actual matchups
                    if resolved_league == "nfl":
                        await create_matchups_internal_nfl(
                            interaction,
                            final_category,
                            all_matchups,
                            game_status,
                            roles_allowed,
                            skip_cpu_vs_cpu=True
                        )
                    else:
                        await create_matchups_internal(
                            interaction, 
                            final_category, 
                            all_matchups, 
                            game_status, 
                            roles_allowed,
                            skip_cpu_vs_cpu=True
                        )
                    self.stop()
                
                @ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
                async def cancel(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.edit_message(
                        content="Matchup creation cancelled.", 
                        embed=None, 
                        view=None
                    )
                    self.stop()
            
            # Check if auto-confirm is enabled
            server_id = str(interaction.guild.id)
            auto_confirm = is_matchup_auto_confirm_enabled(server_id)
            
            if auto_confirm:
                # Auto-confirm enabled: create matchups immediately
                await interaction.followup.send(
                    f"⚡ Creating {len(all_matchups)} matchup(s) from {len(images)} image(s)...",
                    ephemeral=True
                )
                
                # Create the matchups directly
                if resolved_league == "nfl":
                    await create_matchups_internal_nfl(
                        interaction,
                        final_category,
                        all_matchups,
                        game_status,
                        roles_allowed,
                        skip_cpu_vs_cpu=True
                    )
                else:
                    await create_matchups_internal(
                        interaction, 
                        final_category, 
                        all_matchups, 
                        game_status, 
                        roles_allowed,
                        skip_cpu_vs_cpu=True
                    )
            else:
                # Auto-confirm disabled: show confirmation button
                view = ConfirmImageMatchupsView(interaction.user)
                
                # Try to send the preview with retry logic for network issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await interaction.followup.send(embed=preview_embed, view=view, ephemeral=True)
                        break  # Success, exit retry loop
                    except (discord.HTTPException, TimeoutError, asyncio.TimeoutError) as send_error:
                        if attempt < max_retries - 1:
                            print(f"Failed to send preview (attempt {attempt + 1}/{max_retries}): {send_error}")
                            await asyncio.sleep(1)  # Wait 1 second before retry
                        else:
                            # Final attempt failed, try sending a simpler message
                            print(f"All attempts failed to send preview. Error: {send_error}")
                            try:
                                await interaction.followup.send(
                                    "✅ Matchups extracted successfully! However, I couldn't display the preview. "
                                    "Please use the manual creation command or try again.",
                                    ephemeral=True
                                )
                            except:
                                pass
                            raise
            
        except Exception as e:
            print(f"Error in create_matchups_from_image: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing the images. Please try again or use the manual matchup creation command.",
                    ephemeral=True
                )
            except:
                pass


    async def create_matchups_internal(
        interaction: discord.Interaction,
        category_name: str,
        matchups: List[str],
        game_status: bool,
        roles_allowed: str,
        skip_cpu_vs_cpu: bool = False
    ):
        """
        Internal function to create matchups (extracted from your existing create_matchups command)
        This avoids code duplication between manual and image-based creation
        """
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name) or await guild.create_category(category_name)

        # Set permissions
        if roles_allowed:
            roles = [discord.utils.get(guild.roles, name=role.strip()) for role in roles_allowed.split(",")]
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            for role in roles:
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True)
            overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True)
            await category.edit(overwrites=overwrites)
        else:
            await category.edit(overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=True)})

        created_status_messages = []
        channel_names, skipped = [], []
        cpu_vs_cpu_skipped = []

        for matchup in matchups:
            team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                    matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))

            team1_key = clean_team_key(team1_raw.strip())
            team2_key = clean_team_key(team2_raw.strip())
            
            # Check if both teams are CPU (no assigned user)
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), str(guild.id)))
                user1 = cursor.fetchone()
                cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), str(guild.id)))
                user2 = cursor.fetchone()

            # Skip CPU vs CPU games if flag is set
            if skip_cpu_vs_cpu and user1 is None and user2 is None:
                cpu_vs_cpu_skipped.append(matchup)
                continue

            channel_name = matchup.lower().replace(" ", "-")
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                skipped.append(channel_name)
                continue

            channel = await guild.create_text_channel(channel_name, category=category)
            channel_names.append(channel_name)

            team1_cpu = user1 is None
            team2_cpu = user2 is None

            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            if game_status:
                msg = await channel.send(
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1}{' (CPU)' if team1_cpu else ''}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2}{' (CPU)' if team2_cpu else ''}**",
                    silent=True  # Add this line
                )
                await msg.add_reaction("✅")
                await msg.add_reaction("🎲")
                await msg.add_reaction("🟥")
                await msg.add_reaction("🟦")
                created_status_messages.append((channel, msg, team1_key, team2_key))

            await asyncio.sleep(0.1)  # Rate limiting

        # Send success message
        embed = discord.Embed(
            title="📁 Matchup Channels Created from Image",
            description="These matchups were extracted from your image and added to the category:",
            color=discord.Color.green()
        )
        
        if channel_names:
            embed.add_field(
                name=f"🏈 Matchups for **{category_name}** – {len(channel_names)} Total Matchups",
                value="\n".join([name.replace('-', ' ').title() for name in channel_names]),
                inline=False
            )
        if skipped:
            embed.add_field(
                name=f"⚠️ Skipped Duplicate/Existing Channels – {len(skipped)}",
                value="\n".join([name.replace('-', ' ').title() for name in skipped]),
                inline=False
            )
        if cpu_vs_cpu_skipped:
            embed.add_field(
                name=f"🤖 Skipped CPU vs CPU Games – {len(cpu_vs_cpu_skipped)}",
                value="\n".join([f"• {matchup}" for matchup in cpu_vs_cpu_skipped]),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=False)

        # Optional record display prompt
        if game_status and is_record_tracking_enabled(str(interaction.guild.id)) and created_status_messages:
            view = ShowRecordsEditPromptViewUnified(interaction, created_status_messages)
            await interaction.followup.send(
                content="Would you like to update the matchup messages to include team records?",
                view=view,
                ephemeral=True
            )


    # NFL: internal creator (separate from CFB due to table names)
    async def create_matchups_internal_nfl(
        interaction: discord.Interaction,
        category_name: str,
        matchups: List[str],
        game_status: bool,
        roles_allowed: str,
        skip_cpu_vs_cpu: bool = False
    ):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name) or await guild.create_category(category_name)

        if roles_allowed:
            roles = [discord.utils.get(guild.roles, name=role.strip()) for role in roles_allowed.split(",")]
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            for role in roles:
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True)
            overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True)
            await category.edit(overwrites=overwrites)
        else:
            await category.edit(overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=True)})

        created_status_messages = []
        channel_names, skipped = [], []
        cpu_vs_cpu_skipped = []

        for matchup in matchups:
            team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                    matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))

            team1_key = clean_team_key(team1_raw.strip())
            team2_key = clean_team_key(team2_raw.strip())

            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), str(guild.id)))
                user1 = cursor.fetchone()
                cursor.execute("SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), str(guild.id)))
                user2 = cursor.fetchone()

            if skip_cpu_vs_cpu and user1 is None and user2 is None:
                cpu_vs_cpu_skipped.append(matchup)
                continue

            channel_name = matchup.lower().replace(" ", "-")
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                skipped.append(channel_name)
                continue

            channel = await guild.create_text_channel(channel_name, category=category)
            channel_names.append(channel_name)

            team1_cpu = user1 is None
            team2_cpu = user2 is None

            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            if game_status:
                msg = await channel.send(
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1}{' (CPU)' if team1_cpu else ''}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2}{' (CPU)' if team2_cpu else ''}**",
                    silent=True
                )
                await msg.add_reaction("✅")
                await msg.add_reaction("🎲")
                await msg.add_reaction("🟥")
                await msg.add_reaction("🟦")
                created_status_messages.append((channel, msg, team1_key, team2_key))

            await asyncio.sleep(0.1)

        embed = discord.Embed(
            title="📁 Matchup Channels Created",
            description="These matchups were added to your selected category:",
            color=discord.Color.green()
        )
        if channel_names:
            embed.add_field(
                name=f"🏈 Matchups for **{category_name}** – {len(channel_names)} Total Matchups",
                value="\n".join([name.replace('-', ' ').title() for name in channel_names]),
                inline=False
            )
        if skipped:
            embed.add_field(
                name=f"⚠️ Skipped Duplicate/Existing Channels – {len(skipped)}",
                value="\n".join([name.replace('-', ' ').title() for name in skipped]),
                inline=False
            )
        if cpu_vs_cpu_skipped:
            embed.add_field(
                name=f"🤖 Skipped CPU vs CPU Games – {len(cpu_vs_cpu_skipped)}",
                value="\n".join([f"• {m}" for m in cpu_vs_cpu_skipped]),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=False)

        if game_status and is_record_tracking_enabled(str(interaction.guild.id)) and created_status_messages:
            view = ShowRecordsEditPromptViewUnified(interaction, created_messages=created_status_messages)
            await interaction.followup.send(
                content="Would you like to update the matchup messages to include team records?",
                view=view,
                ephemeral=True
            )

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="create-from-text", description="Create matchup channels manually. If > 20 matchups, reuse the command and add the additional.")
    @app_commands.describe(
        category_name="Type a new category name or choose a pre-existing one.",
        game_status="Set this to True to show outcome tracking reactions in each matchup.",
        roles_allowed="Choose roles allowed to view the category.",
        matchup_1="Matchup 1", matchup_2="Matchup 2", matchup_3="Matchup 3", matchup_4="Matchup 4",
        matchup_5="Matchup 5", matchup_6="Matchup 6", matchup_7="Matchup 7", matchup_8="Matchup 8",
        matchup_9="Matchup 9", matchup_10="Matchup 10", matchup_11="Matchup 11", matchup_12="Matchup 12",
        matchup_13="Matchup 13", matchup_14="Matchup 14", matchup_15="Matchup 15", matchup_16="Matchup 16",
        matchup_17="Matchup 17", matchup_18="Matchup 18", matchup_19="Matchup 19", matchup_20="Matchup 20"
    )
    @log_command("matchups create-from-text")
    async def create_matchups(
        interaction: discord.Interaction,
        category_name: str,
        game_status: bool = False,
        roles_allowed: str = "",
        matchup_1: str = None, matchup_2: str = None, matchup_3: str = None, matchup_4: str = None,
        matchup_5: str = None, matchup_6: str = None, matchup_7: str = None, matchup_8: str = None,
        matchup_9: str = None, matchup_10: str = None, matchup_11: str = None, matchup_12: str = None,
        matchup_13: str = None, matchup_14: str = None, matchup_15: str = None, matchup_16: str = None,
        matchup_17: str = None, matchup_18: str = None, matchup_19: str = None, matchup_20: str = None
    ):
        await interaction.response.defer()



        resolved_league = _resolve_league(interaction)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name) or await guild.create_category(category_name)

        if roles_allowed:
            roles = [discord.utils.get(guild.roles, name=role.strip()) for role in roles_allowed.split(",")]
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            for role in roles:
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True)
            overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True)
            await category.edit(overwrites=overwrites)
        else:
            await category.edit(overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=True)})

        matchups = [m for m in [matchup_1, matchup_2, matchup_3, matchup_4, matchup_5, matchup_6, matchup_7, matchup_8,
                                matchup_9, matchup_10, matchup_11, matchup_12, matchup_13, matchup_14, matchup_15,
                                matchup_16, matchup_17, matchup_18, matchup_19, matchup_20] if m]
        if not matchups:
            await interaction.followup.send("You must provide at least one matchup.")
            return

        created_status_messages = []
        channel_names, skipped = [], []

        for matchup in matchups:
            channel_name = matchup.lower().replace(" ", "-")
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                skipped.append(channel_name)
                continue

            channel = await guild.create_text_channel(channel_name, category=category)
            channel_names.append(channel_name)

            team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                    matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))

            team1_key = clean_team_key(team1_raw.strip())
            team2_key = clean_team_key(team2_raw.strip())
            
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                teams_table, _, _ = _tables_for_league(interaction)
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), str(guild.id)))
                user1 = cursor.fetchone()
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), str(guild.id)))
                user2 = cursor.fetchone()

            team1_cpu = user1 is None
            team2_cpu = user2 is None

            
            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            if game_status:
                msg = await channel.send(
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1}{' (CPU)' if team1_cpu else ''}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2}{' (CPU)' if team2_cpu else ''}**",
                    silent=True  # Add this line
                )
                await msg.add_reaction("✅")
                await msg.add_reaction("🎲")
                await msg.add_reaction("🟥")
                await msg.add_reaction("🟦")
                created_status_messages.append((channel, msg, team1_key, team2_key))

        embed = discord.Embed(
            title="📁 Matchup Channels Created",
            description="These matchups were added to your selected category:",
            color=discord.Color.green()
        )
        if channel_names:
            embed.add_field(
                name=f"🏈 Matchups for **{category_name}** – {len(channel_names)} Total Matchups",
                value="\n".join([name.replace('-', ' ').title() for name in channel_names]),
                inline=False
            )
        if skipped:
            embed.add_field(
                name=f"⚠️ Skipped Duplicate/Existing Channels – {len(skipped)}",
                value="\n".join([name.replace('-', ' ').title() for name in skipped]),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=False)

        # 👇 Show optional follow-up record display prompt
        if game_status and is_record_tracking_enabled(str(interaction.guild.id)) and created_status_messages:
            view = ShowRecordsEditPromptViewUnified(interaction, created_status_messages)
            await interaction.followup.send(
                content="Would you like to update the matchup messages to include team records?",
                view=view,
                ephemeral=True
            )

        # Adding a small delay to avoid rate-limiting
        await asyncio.sleep(0.1)  # Adjust the delay if necessary

    # Adding autocomplete for category_name
    @create_matchups.autocomplete("category_name")
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        categories = [category.name for category in guild.categories if current.lower() in category.name.lower()]

        # Allow freetyping and selecting from the existing categories
        choices = [discord.app_commands.Choice(name=category, value=category) for category in categories]
        await interaction.response.autocomplete(choices=choices[:10])

    # Adding autocomplete for matchups
    @create_matchups.autocomplete("matchup_1")
    @create_matchups.autocomplete("matchup_2")
    @create_matchups.autocomplete("matchup_3")
    @create_matchups.autocomplete("matchup_4")
    @create_matchups.autocomplete("matchup_5")
    @create_matchups.autocomplete("matchup_6")
    @create_matchups.autocomplete("matchup_7")
    @create_matchups.autocomplete("matchup_8")
    @create_matchups.autocomplete("matchup_9")
    @create_matchups.autocomplete("matchup_10")
    @create_matchups.autocomplete("matchup_11")
    @create_matchups.autocomplete("matchup_12")
    @create_matchups.autocomplete("matchup_13")
    @create_matchups.autocomplete("matchup_14")
    @create_matchups.autocomplete("matchup_15")
    @create_matchups.autocomplete("matchup_16")
    @create_matchups.autocomplete("matchup_17")
    @create_matchups.autocomplete("matchup_18")
    @create_matchups.autocomplete("matchup_19")
    @create_matchups.autocomplete("matchup_20")
    async def matchup_autocomplete(interaction: discord.Interaction, current: str):
        conn = get_db_connection("matchups")
        cursor = conn.cursor()
        _, _, matchups_table = _tables_for_league(interaction)
        cursor.execute(f"SELECT matchup FROM \"{matchups_table}\" WHERE matchup LIKE ?", (f"{current.lower()}%",))
        rows = cursor.fetchall()
        await interaction.response.autocomplete(choices=[discord.app_commands.Choice(name=m[0], value=m[0]) for m in rows[:10]])
        conn.close()

    # Adding autocomplete for roles_allowed
    @create_matchups.autocomplete("roles_allowed")
    async def roles_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        roles = [role.name for role in guild.roles if current.lower() in role.name.lower()]
        
        # Send autocomplete options for roles
        choices = [discord.app_commands.Choice(name=role, value=role) for role in roles]
        await interaction.response.autocomplete(choices=choices[:10])

    # Autocomplete for category_name in create-from-image
    @create_matchups_from_image.autocomplete("category_name")
    async def category_autocomplete_from_image(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        categories = [category.name for category in guild.categories if current.lower() in category.name.lower()]

        # Allow freetyping and selecting from the existing categories
        choices = [discord.app_commands.Choice(name=category, value=category) for category in categories]
        await interaction.response.autocomplete(choices=choices[:10])

    # Autocomplete for roles_allowed in create-from-image
    @create_matchups_from_image.autocomplete("roles_allowed")
    async def roles_autocomplete_from_image(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []
        roles = [role.name for role in guild.roles if current.lower() in role.name.lower()]
        choices = [discord.app_commands.Choice(name=role, value=role) for role in roles]
        await interaction.response.autocomplete(choices=choices[:10])


    # Command: Delete Matchups
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="delete", description="Delete one or more matchup categories.")
    @app_commands.describe(
        category_1="Category to delete",
        reuse_category="Will you reuse this category? (True = keep category for future use, False = delete everything)",
        category_2="Second category to delete",
        category_3="Third category to delete",
        category_4="Fourth category to delete",
        category_5="Fifth category to delete"
    )
    @log_command("matchups delete")
    async def delete_multiple_categories(
        interaction: discord.Interaction,
        category_1: str,
        reuse_category: bool = False,
        category_2: str = None,
        category_3: str = None,
        category_4: str = None,
        category_5: str = None
    ):


        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.")
            return

        categories_to_delete = [category_1, category_2, category_3, category_4, category_5]
        valid_categories = [discord.utils.get(guild.categories, name=cat) for cat in categories_to_delete if cat]

        if not valid_categories:
            await interaction.response.send_message("❌ No valid categories found to delete.", ephemeral=True)
            return

        # Send confirmation prompt
        class MultiDeleteConfirmView(ui.View):
            def __init__(self, categories, reuse_category):
                super().__init__(timeout=30)
                self.categories = categories
                self.reuse_category = reuse_category

            @ui.button(label="✅ Confirm Delete", style=ButtonStyle.danger)
            async def confirm(self, i: discord.Interaction, button: ui.Button):
                if i.user != interaction.user:
                    await i.response.send_message("You're not allowed to confirm this.", ephemeral=True)
                    return

                await i.response.defer(ephemeral=True)
                deleted_channels = []
                deleted_categories = []

                for category in self.categories:
                    # Always delete all channels in the category
                    for ch in category.channels:
                        await ch.delete()
                        deleted_channels.append(f"{ch.name} (in {category.name})")
                    
                    # Delete or retain the category based on user choice
                    if self.reuse_category:
                        # Keep the category name but remove all channels
                        deleted_categories.append(f"{category.name} (channels deleted, category retained)")
                    else:
                        # Delete the category completely
                        await category.delete()
                        deleted_categories.append(f"{category.name} (completely deleted)")

                # Create appropriate embed based on what was retained
                if self.reuse_category:
                    embed = discord.Embed(
                        title="🧹 Matchups Cleared, Categories Kept",
                        description="The following categories have been cleared of all current matchups and are ready for future use:",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="Categories (Ready for Reuse)",
                        value="\n".join(f"• {cat}" for cat in deleted_categories),
                        inline=False
                    )
                    embed.add_field(
                        name="Cleared Matchups",
                        value="\n".join(f"• {ch}" for ch in deleted_channels[:20]) + (f"\n... and {len(deleted_channels) - 20} more" if len(deleted_channels) > 20 else ""),
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="🗑️ Categories Completely Removed",
                        description="The following categories and all their matchup channels have been permanently deleted:",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Removed Categories",
                        value="\n".join(f"• {cat}" for cat in deleted_categories),
                        inline=False
                    )

                await interaction.followup.send(embed=embed, ephemeral=False)

                self.stop()

            @ui.button(label="Cancel", style=ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, button: ui.Button):
                if i.user != interaction.user:
                    await i.response.send_message("You're not allowed to cancel this.", ephemeral=True)
                    return

                await i.response.send_message("Deletion canceled.", ephemeral=True)
                self.stop()

        names = "\n".join(f"• `{cat.name}`" for cat in valid_categories)
        
        if reuse_category:
            message = f"⚠️ Are you sure you want to **clear all matchups but keep the category for future use**?\n\n**Categories:**\n{names}\n\n✅ **Categories will be kept** for future matchups\n🗑️ **All current matchup channels will be deleted**"
        else:
            message = f"⚠️ Are you sure you want to **completely remove these categories and all their matchups**?\n\n**Categories:**\n{names}\n\n🗑️ **Everything will be permanently deleted** - categories and all channels"
        
        await interaction.response.send_message(
            message,
            view=MultiDeleteConfirmView(valid_categories, reuse_category),
            ephemeral=True
        )
        
    @delete_multiple_categories.autocomplete("category_1")
    @delete_multiple_categories.autocomplete("category_2")
    @delete_multiple_categories.autocomplete("category_3")
    @delete_multiple_categories.autocomplete("category_4")
    @delete_multiple_categories.autocomplete("category_5")
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        matches = [
            cat.name for cat in guild.categories
            if current.lower() in cat.name.lower()
        ]

        return [
            discord.app_commands.Choice(name=name, value=name)
            for name in matches[:10]
        ]


    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="tag-users", description="Tag users in matchup channels.")
    @app_commands.describe(category_name="The name of the category containing the matchup channels.")
    @log_command("matchups tag-users")
    async def tag_users(interaction: discord.Interaction, category_name: str):
        """Tag users in channels within a given category based on team matchups."""

        await interaction.response.defer()
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            await interaction.followup.send(f"Category '{category_name}' not found.", ephemeral=True)
            return

        # Database setup
        conn = get_db_connection("teams")
        cursor = conn.cursor()

        # Special case mappings (before hyphen replacement)
        special_mapping = {
            "texas-am": "texas a&m"
        }

        status_suffixes = {"✅", "🎲", "☑️"}

        for channel in category.channels:
            # Remove status suffix (✅, 🎲, ☑️)
            base_name = channel.name
            for emoji in status_suffixes:
                if base_name.endswith(f"-{emoji}"):
                    base_name = base_name[:-(len(emoji) + 1)]
                    break

            if "-vs-" not in base_name:
                continue

            raw_team1, raw_team2 = base_name.split("-vs-")
            team1_key = clean_team_key(raw_team1)
            team2_key = clean_team_key(raw_team2)

            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            # Fetch user IDs from the DB (try CFB, then NFL)
            cursor.execute(
                "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                (team1_key.lower(), str(guild.id))
            )
            user1 = cursor.fetchone()
            if not user1:
                cursor.execute(
                    "SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team1_key.lower(), str(guild.id))
                )
                user1 = cursor.fetchone()

            cursor.execute(
                "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                (team2_key.lower(), str(guild.id))
            )
            user2 = cursor.fetchone()
            if not user2:
                cursor.execute(
                    "SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team2_key.lower(), str(guild.id))
                )
                user2 = cursor.fetchone()

            user1_id = user1[0] if user1 else None
            user2_id = user2[0] if user2 else None

            # Send message
            if user1_id and user2_id:
                await channel.send(f"**{pretty_team1} vs {pretty_team2}**\n\n<@{user1_id}>\n<@{user2_id}>")
            elif user1_id:
                await channel.send(f"**{pretty_team1} vs CPU ({pretty_team2})**\n\n<@{user1_id}>")
            elif user2_id:
                await channel.send(f"**{pretty_team2} vs CPU ({pretty_team1})**\n\n<@{user2_id}>")
            else:
                await channel.send(f"No representatives found for {pretty_team1} or {pretty_team2}.")

        conn.close()
        embed = discord.Embed(
            title="📣 Users Tagged in Matchup Channels",
            description=f"Player tags completed for matchups in **{category_name}**.",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=False)




    # Autocomplete for category_name
    @tag_users.autocomplete("category_name")
    async def category_name_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild  # Get the guild where the command was used
        if not guild:
            return []

        # Filter categories in the guild based on the current input
        categories = [category.name for category in guild.categories if current.lower() in category.name.lower()]

        # Return up to 10 matching category names
        return [
            discord.app_commands.Choice(name=category, value=category)
            for category in categories[:10]
        ]

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="list-all", description="List all matchups under a specific category.")
    @app_commands.describe(category_name="The name of the category containing matchup channels.")
    @log_command("matchups list-all")
    async def list_matchups_with_users(interaction: discord.Interaction, category_name: str):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            await interaction.response.send_message(f"No category named '{category_name}' found.", ephemeral=True)
            return

        conn = get_db_connection("teams")
        cursor = conn.cursor()

        status_suffixes = {"✅", "🎲", "☑️", "❎", "❌"}
        matchup_channels = []

        for ch in category.channels:
            name = ch.name
            suffix = next((e for e in status_suffixes if name.endswith(f"-{e}")), "")
            if suffix:
                name = name[:-(len(suffix) + 1)]

            if "-vs-" in name:
                matchup_channels.append((ch, name, suffix))

        if not matchup_channels:
            await interaction.response.send_message("No matchup channels found in that category.", ephemeral=True)
            return

        server_id = str(guild.id)
        lines = []

        for ch, raw_name, emoji in matchup_channels:
            team1_raw, team2_raw = raw_name.split("-vs-")
            team1_key = clean_team_key(team1_raw)
            team2_key = clean_team_key(team2_raw)

            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), server_id))
            user1 = cursor.fetchone()
            cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), server_id))
            user2 = cursor.fetchone()

            user1_mention = f"<@{user1[0]}>" if user1 else "CPU"
            user2_mention = f"<@{user2[0]}>" if user2 else "CPU"

            line = f"**{pretty_team1}** vs **{pretty_team2}**\n{user1_mention} vs {user2_mention}{f' {emoji}' if emoji else ''}\n\n"

            lines.append(line)

        conn.close()

        # Combine all lines into a single message
        if lines:
            message_content = f"🆚 **Matchups in {category_name}**\n\n" + "".join(lines)
            
            # Split into chunks if message is too long (Discord limit is 2000 chars)
            if len(message_content) > 2000:
                chunks = []
                current_chunk = f"🆚 **Matchups in {category_name}**\n\n"
                
                for line in lines:
                    if len(current_chunk) + len(line) > 1900:  # Leave some buffer
                        chunks.append(current_chunk)
                        current_chunk = f"🆚 **Matchups in {category_name}** (continued)\n\n"
                    current_chunk += line
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Send private confirmation to user, then post to channel silently
                await interaction.response.send_message("✅ Matchup list posted below.", ephemeral=True)
                
                for chunk in chunks:
                    await interaction.channel.send(chunk, silent=True)
            else:
                # Send private confirmation to user, then post to channel silently
                await interaction.response.send_message("✅ Matchup list posted below.", ephemeral=True)
                await interaction.channel.send(message_content, silent=True)
        else:
            await interaction.response.send_message("No matchups found in that category.", ephemeral=True)



    # Autocomplete for category_name
    @list_matchups_with_users.autocomplete("category_name")
    async def category_name_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        categories = [cat.name for cat in guild.categories if current.lower() in cat.name.lower()]
        return [
            discord.app_commands.Choice(name=cat, value=cat)
            for cat in categories[:10]
        ]

    @matchups_group.command(name="sync-records", description="Update matchup messages in a category to reflect current records.")
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @app_commands.describe(category_name="The name of the matchup category to update.")
    @log_command("matchups sync-records")
    async def update_game_status(interaction: discord.Interaction, category_name: str):
        server_id = str(interaction.guild.id)
        if not is_record_tracking_enabled(server_id):
            await interaction.response.send_message("⚠️ Record tracking is not enabled in this server.", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            await interaction.followup.send(f"❌ No category named '{category_name}' found.", ephemeral=True)
            return

        updated_channels = []

        with get_db_connection("teams") as conn:
            cursor = conn.cursor()

            for channel in category.channels:
                name = strip_status_suffix(channel.name)

                if "-vs-" not in name:
                    continue

                team1_raw, team2_raw = name.split("-vs-")
                team1_key = clean_team_key(team1_raw)
                team2_key = clean_team_key(team2_raw)

                pretty_team1 = format_team_name(team1_key)
                pretty_team2 = format_team_name(team2_key)

                def get_record(team_key):
                    cursor.execute(
                        "SELECT wins, losses FROM cfb_team_records WHERE server_id = ? AND team_name = ?",
                        (server_id, team_key)
                    )
                    return cursor.fetchone() or (0, 0)

                rec1 = get_record(team1_key)
                rec2 = get_record(team2_key)

                cursor.execute(
                    "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team1_key.lower(), server_id)
                )
                user1 = cursor.fetchone()
                cursor.execute(
                    "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team2_key.lower(), server_id)
                )
                user2 = cursor.fetchone()

                team1_cpu = user1 is None
                team2_cpu = user2 is None

                content = (
                    f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                    f"✅ Completed\n"
                    f"🎲 Fair Sim\n"
                    f"🟥 - ☑️ Force Win **{pretty_team1} {'(CPU)' if team1_cpu else f'({rec1[0]}-{rec1[1]})'}**\n"
                    f"🟦 - ☑️ Force Win **{pretty_team2} {'(CPU)' if team2_cpu else f'({rec2[0]}-{rec2[1]})'}**\n\n"
                    "*Records current as of recent sync — may not reflect live records.*"
                )

                try:
                    messages = [msg async for msg in channel.history(limit=10)]
                    target = next(
                        (m for m in messages if m.author.id == interaction.client.user.id and "Game Status Tracker" in m.content),
                        None
                    )
                    if target:
                        await target.edit(content=content)
                        updated_channels.append(channel.name)
                except Exception as e:
                    print(f"[Update Error] Failed in {channel.name}: {e}")

        embed = discord.Embed(
            title="🔄 Game Status Messages Synced",
            description=(
                f"Updated game status messages in `{len(updated_channels)}` channel"
                f"{'s' if len(updated_channels) != 1 else ''} under **{category_name}**."
            ),
            color=discord.Color.blue()
        )

        if updated_channels:
            preview = updated_channels[:10]
            embed.add_field(
                name="✅ Updated Channels",
                value="\n".join(f"• {name}" for name in preview),
                inline=False
            )
            if len(updated_channels) > 10:
                embed.set_footer(text=f"+ {len(updated_channels) - 10} more not shown")
        else:
            embed.description = "No matchup messages were updated. Double-check channel formatting."

        await interaction.followup.send(embed=embed, ephemeral=False)


    @update_game_status.autocomplete("category_name")
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        return [
            discord.app_commands.Choice(name=cat.name, value=cat.name)
            for cat in interaction.guild.categories
            if current.lower() in cat.name.lower()
        ][:10]

    
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="make-public", description="Make a matchup category public and sync all its channels.")
    @app_commands.describe(category_name="Choose a category to make public.")
    @log_command("matchups make-public")
    async def make_public(interaction: discord.Interaction, category_name: str):

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            await interaction.response.send_message(f"No category named '{category_name}' found.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            # Make category public
            overwrite = {guild.default_role: discord.PermissionOverwrite(view_channel=True)}
            await category.edit(overwrites=overwrite)

            # Sync all child channels
            for channel in category.channels:
                try:
                    await channel.edit(sync_permissions=True)
                    await asyncio.sleep(0.1)
                except Exception:
                    continue

            embed = discord.Embed(
                title="🌐 Category Made Public",
                description=f"All channels in **{category_name}** are now visible to everyone in the server.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)



        except Exception as e:
            await interaction.followup.send(f"❌ Error making category public: {e}", ephemeral=True)


    @make_public.autocomplete("category_name")
    async def make_public_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []
        categories = [cat.name for cat in guild.categories if current.lower() in cat.name.lower()]
        return [
            discord.app_commands.Choice(name=cat, value=cat)
            for cat in categories[:10]
        ]

    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @matchups_group.command(name="make-private", description="Make a matchup category private and choose who can view it.")
    @app_commands.describe(
        category_name="The category to make private.",
        roles_allowed="Comma-separated list of role names allowed to view the category."
    )
    @log_command("matchups make-private")
    async def make_category_private(interaction: discord.Interaction, category_name: str, roles_allowed: str):

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            await interaction.response.send_message(f"No category named '{category_name}' found.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        roles = [
            discord.utils.get(guild.roles, name=role_name.strip())
            for role_name in roles_allowed.split(",")
        ]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }

        for role in roles:
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        try:
            await category.edit(overwrites=overwrites)
            for channel in category.channels:
                try:
                    await channel.edit(sync_permissions=True)
                    await asyncio.sleep(0.1)
                except Exception:
                    continue
            
            embed = discord.Embed(
                title="🔒 Category Made Private",
                description=f"All channels in **{category_name}** are now restricted to select roles.",
                color=discord.Color.red()
            )

            # Extract role names with view_channel permission
            allowed_roles = [
                role.name for role, perms in category.overwrites.items()
                if isinstance(role, discord.Role) and perms.view_channel
            ]

            embed.add_field(
                name="👥 Roles with Access",
                value="\n".join(allowed_roles) if allowed_roles else "None (only admins can view)",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=False)


            
        except Exception as e:
            await interaction.followup.send(f"❌ Error making category private: {e}", ephemeral=True)

    @make_category_private.autocomplete("category_name")
    async def private_category_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        categories = [cat.name for cat in guild.categories if current.lower() in cat.name.lower()]
        return [
            discord.app_commands.Choice(name=cat, value=cat)
            for cat in categories[:10]
        ]


    @make_category_private.autocomplete("roles_allowed")
    async def roles_autocomplete(interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        matching_roles = [role.name for role in guild.roles if current.lower() in role.name.lower()]
        return [
            discord.app_commands.Choice(name=role, value=role)
            for role in matching_roles[:10]
        ]
        
    async def autocomplete_target(interaction: Interaction, current: str):
        target_type = interaction.namespace.target_type
        guild = interaction.guild

        if not guild:
            return []

        if target_type == "category":
            return [
                app_commands.Choice(name=cat.name, value=cat.name)
                for cat in guild.categories
                if current.lower() in cat.name.lower()
            ][:25]

        if target_type == "channel":
            return [
                app_commands.Choice(name=ch.name, value=ch.name)
                for ch in guild.text_channels
                if current.lower() in ch.name.lower()
            ][:25]

        return []

    @matchups_group.command(name="add-game-status", description="Apply game status tracker to a week or a specific matchup channel.")
    @subscription_required(allowed_skus=ALL_PREMIUM_SKUS)
    @commissioner_only()
    @app_commands.describe(
        apply_to="Select whether you're targeting a week or a channel.",
        location="Choose a week or a matchup to update matchup statuses."
    )
    @log_command("matchups add-game-status")
    async def add_game_status(
        interaction: discord.Interaction,
        apply_to: Literal["week", "matchup"],
        location: str
    ):
        await interaction.response.defer()
        guild = interaction.guild
        server_id = str(guild.id)

        if not location:
            await interaction.followup.send("❌ You must specify a week or matchup.", ephemeral=True)
            return

        # Determine targets
        targets = []
        if apply_to == "matchup":
            ch = discord.utils.get(guild.text_channels, name=location)
            if not ch:
                await interaction.followup.send(f"❌ Matchup '{location}' not found.", ephemeral=True)
                return
            targets = [ch]
        else:
            cat = discord.utils.get(guild.categories, name=location)
            if not cat:
                await interaction.followup.send(f"❌ Week '{location}' not found.", ephemeral=True)
                return
            targets = cat.channels

        created_status_messages = []

        for ch in targets:
            if "-vs-" not in ch.name:
                continue

            name = strip_status_suffix(ch.name)
            team1_raw, team2_raw = name.split("-vs-")
            team1_key = clean_team_key(team1_raw)
            team2_key = clean_team_key(team2_raw)

            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), server_id))
                user1 = cursor.fetchone()
                cursor.execute("SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), server_id))
                user2 = cursor.fetchone()

            team1_cpu = user1 is None
            team2_cpu = user2 is None

            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)

            # Delete old status message if it exists
            messages = [msg async for msg in ch.history(limit=20)]
            old_tracker = next((m for m in messages if m.author.id == interaction.client.user.id and "Game Status Tracker" in m.content), None)

            if old_tracker:
                try:
                    await old_tracker.delete()
                except Exception as e:
                    print(f"[Cleanup] Could not delete old game status message in {ch.name}: {e}")


            msg = await ch.send(
                f"🏁 **Game Status Tracker**\nReact below to update this matchup's status:\n\n"
                f"✅ Completed\n"
                f"🎲 Fair Sim\n"
                f"🟥 - ☑️ Force Win **{pretty_team1}{' (CPU)' if team1_cpu else ''}**\n"
                f"🟦 - ☑️ Force Win **{pretty_team2}{' (CPU)' if team2_cpu else ''}**",
                silent=True  # Add this line
            )
            await msg.add_reaction("✅")
            await msg.add_reaction("🎲")
            await msg.add_reaction("🟥")
            await msg.add_reaction("🟦")

            created_status_messages.append((ch, msg, team1_key, team2_key))
            await asyncio.sleep(0.1)

        if not created_status_messages:
            await interaction.followup.send("⚠️ No valid matchup channels were updated.", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Game status tracker added to {len(created_status_messages)} matchup(s).", ephemeral=False)

        if is_record_tracking_enabled(server_id):
            view = ShowRecordsEditPromptView(interaction, created_status_messages)
            await interaction.followup.send(
                content="Would you like to update the matchup messages to include team records?",
                view=view,
                ephemeral=True
            )

    @add_game_status.autocomplete("location")
    async def autocomplete_target(interaction: discord.Interaction, current: str):
        apply_to = interaction.namespace.apply_to
        guild = interaction.guild

        if not guild:
            return []

        if apply_to == "week":
            return [
                app_commands.Choice(name=cat.name, value=cat.name)
                for cat in guild.categories
                if current.lower() in cat.name.lower()
            ][:25]

        if apply_to == "matchup":
            return [
                app_commands.Choice(name=ch.name, value=ch.name)
                for ch in guild.text_channels
                if "vs" in ch.name.lower() and current.lower() in ch.name.lower()
            ][:25]

        return []

    # Overview command removed - use /help feature matchups instead
    
    bot.tree.add_command(matchups_group)
