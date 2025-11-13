"""
Command Executor
Executes bot commands based on natural language queries
"""

import discord
from typing import Optional, Dict, Any
from utils.utils import get_db_connection, format_team_name, clean_team_key
from commands.settings import get_server_setting, is_record_tracking_enabled, get_commissioner_roles
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import time
from .token_tracker import get_tracker

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def execute_command(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[str]:
    """
    Execute a command based on natural language query
    
    Args:
        bot: Discord bot instance
        message: Original message
        query: User's natural language query
        server_id: Server ID
        
    Returns:
        Response message if command was executed, None otherwise
    """
    query_lower = query.lower()
    
    # Check for executable commands (prioritize most specific first)
    
    # Points queries
    if any(phrase in query_lower for phrase in ["my points", "how many points", "points do i have", "what's my points", "what is my points"]):
        return await execute_my_points(message.author.id, server_id)
    
    # Team assignment queries
    if any(phrase in query_lower for phrase in ["who has", "who owns"]):
        team_name = extract_team_name(query)
        if team_name:
            return await execute_who_has(message, team_name, server_id)
    
    # List all teams
    if any(phrase in query_lower for phrase in ["list all teams", "all teams", "all assignments", "show all teams", "view all teams"]):
        return await execute_list_all_teams(message.guild, server_id)
    
    # My team
    if any(phrase in query_lower for phrase in ["my team", "what team", "which team", "what's my team", "what is my team"]):
        return await execute_my_team(message.author.id, server_id)
    
    # Record queries
    if any(phrase in query_lower for phrase in ["check record", "team record", "record for", "what's the record", "what is the record"]):
        team_name = extract_team_name(query)
        if team_name:
            return await execute_check_record(message.guild, team_name, server_id)
    
    # All records/standings
    if any(phrase in query_lower for phrase in ["all records", "view all records", "standings", "league standings", "show standings"]):
        return await execute_view_all_records(message.guild, server_id)
    
    # Pending requests
    if any(phrase in query_lower for phrase in ["pending requests", "my requests", "request status", "my pending"]):
        return await execute_pending_requests(message.author.id, server_id)
    
    # Request history
    if any(phrase in query_lower for phrase in ["request history", "my history", "attribute history", "upgrade history"]):
        # Check if asking about someone else's history
        target_user = extract_user_mention(message, query)
        if target_user and is_commissioner(message.author, server_id):
            return await execute_request_history(message.author.id, server_id, target_user.id)
        else:
            return await execute_request_history(message.author.id, server_id, message.author.id)
    
    # Matchups list
    if any(phrase in query_lower for phrase in ["list matchups", "show matchups", "matchups in", "matchups for"]):
        category_name = extract_category_name(query)
        if category_name:
            return await execute_list_matchups(message.guild, category_name, server_id)
    
    # Check user points (commissioner only)
    if any(phrase in query_lower for phrase in ["check user points", "points for", "how many points does"]):
        if is_commissioner(message.author, server_id):
            target_user = extract_user_mention(message, query)
            if target_user:
                return await execute_check_user_points(message.guild, target_user.id, server_id)
    
    # Check all points (commissioner only)
    if any(phrase in query_lower for phrase in ["all points", "everyone's points", "all users points", "points for everyone"]):
        if is_commissioner(message.author, server_id):
            return await execute_check_all_points(message.guild, server_id)
    
    # View settings (commissioner only)
    if any(phrase in query_lower for phrase in ["server settings", "view settings", "show settings", "current settings"]):
        if is_commissioner(message.author, server_id):
            return await execute_view_settings(message.guild, server_id)
    
    # Create matchups from image (write command)
    if message.attachments and any(phrase in query_lower for phrase in [
        "create matchups", "create from image", "matchups from image", 
        "create from this", "extract matchups", "process image"
    ]):
        if is_commissioner(message.author, server_id):
            return await execute_create_from_image(bot, message, query, server_id)
    
    # Delete matchup categories (write command)
    # Check for delete/remove/clear keywords combined with matchup-related terms
    delete_keywords = ["delete", "remove", "clear"]
    matchup_terms = ["matchup", "matchups", "category", "categories", "week"]
    
    has_delete_keyword = any(keyword in query_lower for keyword in delete_keywords)
    has_matchup_term = any(term in query_lower for term in matchup_terms)
    
    # Also check for specific phrases
    delete_phrases = [
        "delete matchups", "delete categories", "remove matchups", "remove categories",
        "delete category", "remove category", "clear matchups", "delete week", "remove week"
    ]
    has_delete_phrase = any(phrase in query_lower for phrase in delete_phrases)
    
    if has_delete_phrase or (has_delete_keyword and has_matchup_term):
        if is_commissioner(message.author, server_id):
            return await execute_delete_categories(bot, message, query, server_id)
    
    # Tag users in matchups (write command)
    if any(phrase in query_lower for phrase in [
        "tag users", "tag players", "notify users", "mention users",
        "tag users in", "tag players in", "notify players"
    ]):
        if is_commissioner(message.author, server_id):
            return await execute_tag_users(bot, message, query, server_id)
    
    # Announce advance (write command)
    if any(phrase in query_lower for phrase in [
        "announce advance", "announce week", "advance announcement",
        "notify advance", "post advance", "send advance"
    ]):
        if is_commissioner(message.author, server_id):
            return await execute_announce_advance(bot, message, query, server_id)
    
    # If no command matched, return None (will fall back to regular conversation)
    return None


async def execute_my_points(user_id: int, server_id: str) -> str:
    """Execute /attributes my-points"""
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user_id, server_id)
            )
            row = cursor.fetchone()
        
        points = row[0] if row else 0
        return f"🧮 You currently have **{points} attribute point{'s' if points != 1 else ''}** available."
    except Exception as e:
        return f"⚠️ Couldn't check your points right now. Try using `/attributes my-points` instead."


async def execute_who_has(message: discord.Message, team_name: str, server_id: str) -> str:
    """Execute /teams who-has"""
    try:
        # Determine league type
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        teams_table = "nfl_teams" if league_type.lower() == "nfl" else "cfb_teams"
        
        team_key = clean_team_key(team_name.lower())
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?",
                (team_key, server_id)
            )
            user = cursor.fetchone()
        
        pretty_team = format_team_name(team_key)
        if user:
            return f"**{pretty_team}** is assigned to <@{user[0]}>."
        else:
            return f"**{pretty_team}** is not assigned to anyone (CPU)."
    except Exception as e:
        return f"⚠️ Couldn't check team assignment. Try using `/teams who-has team:{team_name}` instead."


async def execute_list_all_teams(guild: discord.Guild, server_id: str) -> str:
    """Execute /teams list-all"""
    try:
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        teams_table = "nfl_teams" if league_type.lower() == "nfl" else "cfb_teams"
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT team_name, user_id FROM {teams_table} WHERE server_id = ? ORDER BY team_name",
                (server_id,)
            )
            records = cursor.fetchall()
        
        if not records:
            return "📭 No team assignments found in this server."
        
        lines = ["📋 **Team Assignments:**\n"]
        for team_name, user_id in records:
            pretty_team = format_team_name(team_name)
            if user_id:
                user = guild.get_member(user_id)
                user_display = user.display_name if user else f"<@{user_id}>"
                lines.append(f"• **{pretty_team}** → {user_display}")
            else:
                lines.append(f"• **{pretty_team}** → CPU")
        
        result = "\n".join(lines)
        # Discord message limit is 2000 chars
        if len(result) > 1900:
            result = "\n".join(lines[:30])
            result += f"\n\n... and {len(records) - 30} more teams. Use `/teams list-all` to see all."
        
        return result
    except Exception as e:
        return "⚠️ Couldn't list teams right now. Try using `/teams list-all` instead."


async def execute_my_team(user_id: int, server_id: str) -> str:
    """Get user's team assignment"""
    try:
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        teams_table = "nfl_teams" if league_type.lower() == "nfl" else "cfb_teams"
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT team_name FROM {teams_table} WHERE user_id = ? AND server_id = ?",
                (user_id, server_id)
            )
            row = cursor.fetchone()
        
        if row:
            pretty_team = format_team_name(row[0])
            return f"🏈 You're assigned to **{pretty_team}**."
        else:
            return "📭 You don't have a team assigned yet. Ask a commissioner to assign you one!"
    except Exception as e:
        return "⚠️ Couldn't check your team assignment right now."


async def execute_check_record(guild: discord.Guild, team_name: str, server_id: str) -> str:
    """Execute /records check-record"""
    if not is_record_tracking_enabled(server_id):
        return "⚠️ Record tracking is not enabled in this server."
    
    try:
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        records_table = "nfl_team_records" if league_type.lower() == "nfl" else "cfb_team_records"
        
        team_key = clean_team_key(team_name.lower())
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT wins, losses FROM {records_table} WHERE server_id = ? AND team_name = ?",
                (server_id, team_key)
            )
            record = cursor.fetchone()
        
        pretty_team = format_team_name(team_key)
        if record:
            wins, losses = record
            return f"📊 **{pretty_team}**: {wins}-{losses}"
        else:
            return f"📊 **{pretty_team}**: No record yet (0-0)"
    except Exception as e:
        return f"⚠️ Couldn't check record. Try using `/records check-record team:{team_name}` instead."


async def execute_view_all_records(guild: discord.Guild, server_id: str) -> str:
    """Execute /records view-all-records"""
    if not is_record_tracking_enabled(server_id):
        return "⚠️ Record tracking is not enabled in this server."
    
    try:
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        records_table = "nfl_team_records" if league_type.lower() == "nfl" else "cfb_team_records"
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT team_name, wins, losses FROM {records_table} WHERE server_id = ? ORDER BY wins DESC, losses ASC",
                (server_id,)
            )
            records = cursor.fetchall()
        
        if not records:
            return "📭 No records found in this server."
        
        lines = ["📊 **League Standings:**\n"]
        for team_name, wins, losses in records:
            pretty_team = format_team_name(team_name)
            lines.append(f"• **{pretty_team}**: {wins}-{losses}")
        
        result = "\n".join(lines)
        if len(result) > 1900:
            result = "\n".join(lines[:30])
            result += f"\n\n... and {len(records) - 30} more teams. Use `/records view-all-records` to see all."
        
        return result
    except Exception as e:
        return "⚠️ Couldn't view records right now. Try using `/records view-all-records` instead."


async def execute_pending_requests(user_id: int, server_id: str) -> str:
    """Get user's pending attribute requests"""
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT request_number, player, attribute, amount
                   FROM attribute_requests
                   WHERE user_id = ? AND server_id = ? AND status = 'pending'
                   ORDER BY request_number DESC
                   LIMIT 10""",
                (user_id, server_id)
            )
            requests = cursor.fetchall()
        
        if not requests:
            return "✅ You have no pending attribute requests."
        
        lines = ["⏳ **Your Pending Requests:**\n"]
        for req_id, player, attribute, amount in requests:
            lines.append(f"• Request #{req_id}: {amount}pt for {attribute} on {player}")
        
        return "\n".join(lines)
    except Exception as e:
        return "⚠️ Couldn't check your requests. Try using `/attributes pending` instead."


def extract_team_name(query: str) -> Optional[str]:
    """
    Extract team name from query using simple heuristics
    
    Args:
        query: User's query
        
    Returns:
        Team name if found, None otherwise
    """
    query_lower = query.lower()
    
    # Common patterns
    patterns = [
        r"who has (.+)",
        r"who owns (.+)",
        r"record for (.+)",
        r"record of (.+)",
        r"(.+) record",
        r"check (.+)",
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            team = match.group(1).strip()
            # Remove common trailing words
            team = re.sub(r'\s+(record|team|assignment|has|owns)$', '', team)
            if team and len(team) > 2:
                return team
    
    # If no pattern matched, try to find team name after keywords
    keywords = ["who has", "who owns", "record for", "check"]
    for keyword in keywords:
        if keyword in query_lower:
            parts = query_lower.split(keyword, 1)
            if len(parts) > 1:
                team = parts[1].strip()
                # Remove question marks and common words
                team = re.sub(r'[?\.!]', '', team)
                team = re.sub(r'\s+(record|team|assignment)$', '', team)
                if team and len(team) > 2:
                    return team
    
    return None


def is_commissioner(user: discord.Member, server_id: str) -> bool:
    """Check if user is a commissioner"""
    try:
        commissioner_roles = get_commissioner_roles(server_id)
        user_roles = {role.name for role in user.roles}
        return bool(user_roles & commissioner_roles) or user.guild_permissions.administrator
    except:
        return False


async def execute_create_from_image(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[str]:
    """Execute /matchups create-from-image - process images and create matchups"""
    try:
        # Check if user is commissioner
        if not is_commissioner(message.author, server_id):
            return "🚫 You must be a commissioner to create matchups."
        
        # Get images from attachments
        images = [att for att in message.attachments if att.content_type and att.content_type.startswith('image/')]
        
        if not images:
            return "⚠️ No images found in your message. Please attach image(s) containing matchup schedules."
        
        if len(images) > 5:
            return "⚠️ Too many images. Please attach up to 5 images."
        
        # Validate image sizes
        for img in images:
            if img.size > 10 * 1024 * 1024:  # 10MB limit
                return f"❌ Image '{img.filename}' is too large. Please use images under 10MB."
        
        # Agent 1: Extract parameters from natural language
        extracted_params = await extract_create_from_image_params(query, message.guild)
        
        # Agent 2: Validate and resolve parameters
        validated_params = await validate_create_from_image_params(extracted_params, message.guild, server_id)
        
        if validated_params.get('error'):
            return validated_params['error']
        
        category_name = validated_params['category_name']
        game_status = validated_params['game_status']
        roles_allowed = validated_params['roles_allowed']
        
        # Process images (this will take time, so send a "processing" message first)
        processing_msg = await message.channel.send("🔄 Processing images... This may take a moment.")
        
        # Import the processing function
        from commands.matchups import process_matchup_image
        from commands.settings import get_server_setting
        
        # Determine league type
        league_type = get_server_setting(server_id, "league_type") or "cfb"
        resolved_league = league_type.lower()
        
        all_matchups = []
        all_categories = []
        
        # Process each image
        for i, image in enumerate(images, 1):
            try:
                extracted_category, matchups = await process_matchup_image(image.url)
                
                if extracted_category and matchups:
                    all_categories.append(f"Image {i}: {extracted_category}")
                    all_matchups.extend(matchups)
                    # Use extracted category if we don't have one from query/params
                    if not category_name or category_name == "Week 1":
                        category_name = extracted_category
                else:
                    await message.channel.send(
                        f"⚠️ Could not extract matchup information from image {i}. Skipping this image."
                    )
            except Exception as e:
                print(f"[Create from Image] Error processing image {i}: {e}")
                await message.channel.send(
                    f"⚠️ Error processing image {i}: {str(e)[:100]}"
                )
        
        # Delete processing message
        try:
            await processing_msg.delete()
        except:
            pass
        
        if not all_matchups:
            return "❌ Could not extract matchup information from any of the images. Please make sure the images clearly show team matchups."
        
        # Check for CPU vs CPU games
        from utils.utils import get_db_connection
        cpu_vs_cpu_count = 0
        teams_table = "nfl_teams" if resolved_league == "nfl" else "cfb_teams"
        
        with get_db_connection("teams") as conn:
            cursor = conn.cursor()
            for matchup in all_matchups:
                team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                        matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))
                team1_key = clean_team_key(team1_raw.strip())
                team2_key = clean_team_key(team2_raw.strip())
                
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", 
                             (team1_key.lower(), server_id))
                user1 = cursor.fetchone()
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", 
                             (team2_key.lower(), server_id))
                user2 = cursor.fetchone()
                
                if user1 is None and user2 is None:
                    cpu_vs_cpu_count += 1
        
        # Create preview embed
        preview_embed = discord.Embed(
            title="🔍 Extracted Matchup Information",
            description=f"**Category:** {category_name}\n\n**Found {len(all_matchups)} total matchups from {len(images)} image(s):**",
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
        
        # Add settings info
        settings_info = []
        if game_status:
            settings_info.append("✅ Game Status Tracking: Enabled")
        if roles_allowed:
            settings_info.append(f"🔒 Roles Allowed: {roles_allowed}")
        if settings_info:
            preview_embed.add_field(
                name="⚙️ Settings",
                value="\n".join(settings_info),
                inline=False
            )
        
        # Create confirmation view
        from discord import ui, ButtonStyle
        
        class ConfirmImageMatchupsView(ui.View):
            def __init__(self, original_user, category_name, matchups, league_type, server_id, game_status, roles_allowed):
                super().__init__(timeout=300)  # 5 minute timeout
                self.original_user = original_user
                self.category_name = category_name
                self.matchups = matchups
                self.league_type = league_type
                self.server_id = server_id
                self.game_status = game_status
                self.roles_allowed = roles_allowed
                self.confirmed = False
            
            @ui.button(label="✅ Create These Matchups", style=ButtonStyle.success)
            async def confirm(self, interaction: discord.Interaction, button: ui.Button):
                if interaction.user.id != self.original_user.id:
                    await interaction.response.send_message("Only the original user can confirm this.", ephemeral=True)
                    return
                
                self.confirmed = True
                # Defer the response so we can send followup messages
                await interaction.response.defer(thinking=True)
                
                # Edit the message to show we're creating
                try:
                    await interaction.edit_original_response(
                        content="Creating matchups...", 
                        embed=None, 
                        view=None
                    )
                except:
                    pass
                
                # Create the matchups
                await create_matchups_from_extracted(
                    interaction,
                    self.category_name,
                    self.matchups,
                    self.league_type,
                    self.server_id,
                    self.game_status,
                    self.roles_allowed
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
        
        view = ConfirmImageMatchupsView(
            message.author,
            category_name,
            all_matchups,
            resolved_league,
            server_id,
            game_status,
            roles_allowed
        )
        
        preview_msg = await message.channel.send(embed=preview_embed, view=view)
        
        # Return None so the conversation handler doesn't send another message
        return None
        
    except Exception as e:
        import traceback
        print(f"[Create from Image] Error: {e}")
        print(f"[Create from Image] Traceback: {traceback.format_exc()}")
        return f"⚠️ Error processing images: {str(e)[:150]}"


async def extract_create_from_image_params(query: str, guild: discord.Guild) -> Dict[str, Any]:
    """
    Agent 1: Extract parameters from natural language query
    
    Returns:
        Dict with category_name, game_status, roles_allowed
    """
    if not client:
        # Fallback to simple extraction
        return {
            'category_name': extract_category_name_from_query(query),
            'game_status': detect_game_status_in_query(query),
            'roles_allowed': extract_roles_from_query(query)
        }
    
    # Get available roles for context
    available_roles = [role.name for role in guild.roles if role.name != "@everyone"][:20]  # Limit for context
    
    prompt = f"""Extract parameters from this user query about creating matchups from images:

Query: "{query}"

Extract the following:
1. **category_name**: The category/channel name (e.g., "Week 0", "Week 1", "Playoffs", "Championship")
   - Look for phrases like "name channel", "category", "for week", "week X"
   - If found, extract it. If not, return null.

2. **game_status**: Boolean - whether to add game status trackers
   - Look for: "game status", "status tracker", "tracking", "add reactions", "game tracker"
   - Return true if mentioned, false otherwise

3. **roles_allowed**: Comma-separated list of role names that should have access
   - Look for: "commissioners allowed", "only admins", "role X can see", "private to role Y"
   - Extract role names mentioned
   - Available roles on server: {', '.join(available_roles[:15])}

Return ONLY a JSON object with these three fields:
{{
    "category_name": "Week 0" or null,
    "game_status": true or false,
    "roles_allowed": "Commish,Admin" or ""
}}

Examples:
- "Create matchups from this image. Name channel Week 0, add game status trackers, commissioners allowed"
  → {{"category_name": "Week 0", "game_status": true, "roles_allowed": "Commissioners"}}

- "Extract matchups for Week 1 with game status"
  → {{"category_name": "Week 1", "game_status": true, "roles_allowed": ""}}

- "Create matchups from image, make it private to Commish role"
  → {{"category_name": null, "game_status": false, "roles_allowed": "Commish"}}

Return JSON only, no other text."""

    try:
        start_time = time.time()
        tracker = get_tracker()
        input_tokens = tracker.estimate_tokens(prompt)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Log token usage
        output_tokens = tracker.estimate_tokens(result_text)
        duration_ms = (time.time() - start_time) * 1000
        tracker.log_usage("command_extract_create_params", "gpt-4o-mini", input_tokens, output_tokens, duration_ms)
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        extracted = json.loads(result_text)
        print(f"[Extract Params] Extracted: {extracted}")
        return extracted
    except json.JSONDecodeError as e:
        print(f"[Extract Params] JSON decode error: {e}")
        print(f"[Extract Params] Raw response: {result_text[:200]}")
        # Fallback
        return {
            'category_name': extract_category_name_from_query(query),
            'game_status': detect_game_status_in_query(query),
            'roles_allowed': extract_roles_from_query(query)
        }
    except Exception as e:
        print(f"[Extract Params] Error: {e}")
        # Fallback
        return {
            'category_name': extract_category_name_from_query(query),
            'game_status': detect_game_status_in_query(query),
            'roles_allowed': extract_roles_from_query(query)
        }


async def validate_create_from_image_params(params: Dict[str, Any], guild: discord.Guild, server_id: str) -> Dict[str, Any]:
    """
    Agent 2: Validate and resolve parameters
    
    Returns:
        Dict with validated parameters or error message
    """
    validated = {
        'category_name': None,
        'game_status': False,
        'roles_allowed': "",
        'error': None
    }
    
    # Validate category_name
    category_name = params.get('category_name')
    if category_name:
        # Clean up the category name
        category_name = category_name.strip()
        if len(category_name) > 0:
            validated['category_name'] = category_name
    
    # Validate game_status (should be boolean)
    game_status = params.get('game_status', False)
    if isinstance(game_status, bool):
        validated['game_status'] = game_status
    elif isinstance(game_status, str):
        validated['game_status'] = game_status.lower() in ['true', 'yes', '1', 'on']
    else:
        validated['game_status'] = False
    
    # Validate roles_allowed - check if roles exist on server
    roles_allowed = params.get('roles_allowed', '')
    if roles_allowed:
        # Split by comma and validate each role
        role_names = [r.strip() for r in roles_allowed.split(',')]
        valid_roles = []
        invalid_roles = []
        
        for role_name in role_names:
            # Check if role exists
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                valid_roles.append(role_name)
            else:
                invalid_roles.append(role_name)
        
        if invalid_roles:
            validated['error'] = f"❌ The following roles don't exist on this server: {', '.join(invalid_roles)}\n\nAvailable roles: {', '.join([r.name for r in guild.roles if r.name != '@everyone'][:10])}"
            return validated
        
        validated['roles_allowed'] = ','.join(valid_roles)
    
    return validated


def detect_game_status_in_query(query: str) -> bool:
    """Detect if game status tracking is requested"""
    query_lower = query.lower()
    game_status_keywords = [
        "game status", "status tracker", "tracking", "add reactions",
        "game tracker", "track games", "status tracking", "with status"
    ]
    return any(keyword in query_lower for keyword in game_status_keywords)


def extract_roles_from_query(query: str) -> str:
    """Extract role names from query"""
    import re
    
    query_lower = query.lower()
    
    # Patterns to find roles
    patterns = [
        r"([a-zA-Z\s]+)\s+allowed",
        r"only\s+([a-zA-Z\s]+)",
        r"private\s+to\s+([a-zA-Z\s]+)",
        r"role[s]?\s+([a-zA-Z\s,]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            roles = match.group(1).strip()
            # Remove common words
            roles = re.sub(r'\s+(role|roles|allowed|can|see|view)$', '', roles, flags=re.IGNORECASE)
            if roles and len(roles) > 2:
                return roles
    
    return ""


def extract_category_name_from_query(query: str) -> Optional[str]:
    """Extract category name from query - fallback function"""
    import re
    
    query_lower = query.lower()
    
    # Patterns to extract category - prioritize "name channel" and week numbers
    patterns = [
        r"name\s+channel\s+(.+)",  # "name channel Week 0"
        r"category[:\s]+(.+)",
        r"for\s+(week\s+\d+|.+)",  # "for Week 0" or "for Playoffs"
        r"week\s+(\d+)",  # "Week 0", "week 1", etc.
        r"(.+?)\s+matchups",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            category = match.group(1).strip()
            # Remove common trailing words
            category = re.sub(r'\s+(matchups|category|from|image|this|channel)$', '', category)
            if category and len(category) > 0:
                # If it's just a number, format as "Week N"
                if category.isdigit():
                    return f"Week {category}"
                # If it starts with "week" and has a number, extract it
                week_match = re.search(r"week\s*(\d+)", category, re.IGNORECASE)
                if week_match:
                    return f"Week {week_match.group(1)}"
                return category.title()
    
    # Check for "this week" or "current week"
    if "this week" in query_lower or "current week" in query_lower:
        return None
    
    return None


async def create_matchups_from_extracted(
    interaction: discord.Interaction,
    category_name: str,
    matchups: list,
    league_type: str,
    server_id: str,
    game_status: bool = False,
    roles_allowed: str = ""
):
    """Create matchups from extracted data"""
    try:
        import asyncio
        from utils.utils import get_db_connection
        
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name) or await guild.create_category(category_name)
        
        # Set permissions based on roles_allowed
        if roles_allowed:
            roles = [discord.utils.get(guild.roles, name=role.strip()) for role in roles_allowed.split(",")]
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            for role in roles:
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True)
            overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True)
            await category.edit(overwrites=overwrites)
        else:
            # Default to public
            await category.edit(overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=True)})
        
        created_channels = []
        skipped = []
        cpu_vs_cpu_skipped = []
        
        teams_table = "nfl_teams" if league_type == "nfl" else "cfb_teams"
        
        for matchup in matchups:
            team1_raw, team2_raw = (matchup.split(" vs ") if " vs " in matchup else
                                    matchup.split("-vs-") if "-vs-" in matchup else ("Team 1", "Team 2"))
            
            team1_key = clean_team_key(team1_raw.strip())
            team2_key = clean_team_key(team2_raw.strip())
            
            # Check if both teams are CPU (no assigned user)
            with get_db_connection("teams") as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", 
                             (team1_key.lower(), server_id))
                user1 = cursor.fetchone()
                cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", 
                             (team2_key.lower(), server_id))
                user2 = cursor.fetchone()
            
            # Skip CPU vs CPU games
            if user1 is None and user2 is None:
                cpu_vs_cpu_skipped.append(matchup)
                continue
            
            channel_name = matchup.lower().replace(" ", "-")
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                skipped.append(channel_name)
                continue
            
            channel = await guild.create_text_channel(channel_name, category=category)
            created_channels.append(channel_name)
            
            # Add game status tracking if enabled
            if game_status:
                team1_cpu = user1 is None
                team2_cpu = user2 is None
                pretty_team1 = format_team_name(team1_key)
                pretty_team2 = format_team_name(team2_key)
                
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
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        # Send success message
        embed = discord.Embed(
            title="📁 Matchup Channels Created from Image",
            description="These matchups were extracted from your image and added to the category:",
            color=discord.Color.green()
        )
        
        if created_channels:
            embed.add_field(
                name=f"🏈 Matchups for **{category_name}** – {len(created_channels)} Total Matchups",
                value="\n".join([name.replace('-', ' ').title() for name in created_channels[:20]]),
                inline=False
            )
            if len(created_channels) > 20:
                embed.add_field(
                    name="...",
                    value=f"and {len(created_channels) - 20} more matchups",
                    inline=False
                )
        
        if skipped:
            embed.add_field(
                name=f"⚠️ Skipped Duplicate/Existing Channels – {len(skipped)}",
                value="\n".join([name.replace('-', ' ').title() for name in skipped[:10]]),
                inline=False
            )
        
        if cpu_vs_cpu_skipped:
            embed.add_field(
                name=f"🤖 Skipped CPU vs CPU Games – {len(cpu_vs_cpu_skipped)}",
                value="\n".join([f"• {matchup}" for matchup in cpu_vs_cpu_skipped[:10]]),
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        
    except Exception as e:
        import traceback
        print(f"[Create Matchups] Error: {e}")
        print(f"[Create Matchups] Traceback: {traceback.format_exc()}")
        await interaction.followup.send(
            f"❌ Error creating matchups: {str(e)[:150]}",
            ephemeral=True
        )


# ============================================================================
# DELETE CATEGORIES AGENTIC SYSTEM
# ============================================================================

async def execute_delete_categories(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[str]:
    """Execute /matchups delete - delete matchup categories"""
    try:
        # Check if user is commissioner
        if not is_commissioner(message.author, server_id):
            return "🚫 You must be a commissioner to delete matchup categories."
        
        if not message.guild:
            return "⚠️ This command can only be used in a server."
        
        # Agent 1: Extract parameters from natural language
        extracted_params = await extract_delete_params(query, message.guild)
        
        # Agent 2: Validate and resolve parameters
        validated_params = await validate_delete_params(extracted_params, message.guild)
        
        if validated_params.get('error'):
            return validated_params['error']
        
        categories_to_delete = validated_params['categories']
        reuse_category = validated_params['reuse_category']
        
        if not categories_to_delete:
            return "❌ No valid categories found to delete. Please specify category names like 'Week 1' or 'Playoffs'."
        
        # Create preview embed
        category_list = "\n".join([f"• {cat.name}" for cat in categories_to_delete])
        total_channels = sum(len(cat.channels) for cat in categories_to_delete)
        
        preview_embed = discord.Embed(
            title="🗑️ Delete Matchup Categories",
            description=f"**Found {len(categories_to_delete)} category/categories to delete:**",
            color=discord.Color.orange()
        )
        
        preview_embed.add_field(
            name="Categories",
            value=category_list,
            inline=False
        )
        
        preview_embed.add_field(
            name="Total Channels",
            value=f"{total_channels} matchup channel(s) will be deleted",
            inline=False
        )
        
        if reuse_category:
            preview_embed.add_field(
                name="⚠️ Category Retention",
                value="Categories will be kept for future use (only channels will be deleted)",
                inline=False
            )
        else:
            preview_embed.add_field(
                name="⚠️ Complete Deletion",
                value="Categories and all channels will be permanently deleted",
                inline=False
            )
        
        # Create confirmation view
        from discord import ui, ButtonStyle
        
        class ConfirmDeleteCategoriesView(ui.View):
            def __init__(self, original_user, categories, reuse_category):
                super().__init__(timeout=300)  # 5 minute timeout
                self.original_user = original_user
                self.categories = categories
                self.reuse_category = reuse_category
                self.confirmed = False
            
            @ui.button(label="✅ Confirm Delete", style=ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: ui.Button):
                if interaction.user.id != self.original_user.id:
                    await interaction.response.send_message("Only the original user can confirm this.", ephemeral=True)
                    return
                
                self.confirmed = True
                # Defer the response so we can send followup messages
                await interaction.response.defer(thinking=True)
                
                # Edit the message to show we're deleting
                try:
                    await interaction.edit_original_response(
                        content="Deleting categories...", 
                        embed=None, 
                        view=None
                    )
                except:
                    pass
                
                # Delete the categories
                await delete_categories_from_extracted(
                    interaction,
                    self.categories,
                    self.reuse_category
                )
                self.stop()
            
            @ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: ui.Button):
                await interaction.response.edit_message(
                    content="Category deletion cancelled.", 
                    embed=None, 
                    view=None
                )
                self.stop()
        
        view = ConfirmDeleteCategoriesView(
            message.author,
            categories_to_delete,
            reuse_category
        )
        
        preview_msg = await message.channel.send(embed=preview_embed, view=view)
        
        # Return None so the conversation handler doesn't send another message
        return None
        
    except Exception as e:
        import traceback
        print(f"[Delete Categories] Error: {e}")
        print(f"[Delete Categories] Traceback: {traceback.format_exc()}")
        return f"⚠️ Error processing delete request: {str(e)[:150]}"


async def extract_delete_params(query: str, guild: discord.Guild) -> Dict[str, Any]:
    """
    Agent 1: Extract parameters from natural language query
    
    Returns:
        Dict with categories (list of strings) and reuse_category (bool)
    """
    if not client:
        # Fallback to simple extraction
        return {
            'categories': extract_category_names_from_query(query),
            'reuse_category': detect_reuse_category_in_query(query)
        }
    
    # Get available categories for context
    available_categories = [cat.name for cat in guild.categories if cat][:20]
    
    prompt = f"""Extract parameters from this user query about deleting matchup categories:

Query: "{query}"

Extract the following:
1. **categories**: List of category names to delete (e.g., ["Week 1", "Week 2", "Playoffs"])
   - Look for phrases like "delete Week 1", "remove Week 2 and Week 3", "delete categories Week 1, Week 2"
   - Extract all category names mentioned
   - Can be up to 5 categories
   - Return as a JSON array of strings

2. **reuse_category**: Boolean - whether to keep categories for future use
   - Look for: "keep category", "reuse", "keep for future", "retain category", "keep the category"
   - Return true if mentioned, false otherwise
   - Default is false (complete deletion)

Available categories on server: {', '.join(available_categories[:15])}

Return ONLY a JSON object with these two fields:
{{
    "categories": ["Week 1", "Week 2"] or [],
    "reuse_category": true or false
}}

Examples:
- "Delete Week 1 and Week 2, keep the categories"
  → {{"categories": ["Week 1", "Week 2"], "reuse_category": true}}

- "Remove Week 1 completely"
  → {{"categories": ["Week 1"], "reuse_category": false}}

- "Delete Week 1, Week 2, and Week 3"
  → {{"categories": ["Week 1", "Week 2", "Week 3"], "reuse_category": false}}

- "Clear matchups from Week 1 but keep the category"
  → {{"categories": ["Week 1"], "reuse_category": true}}

Return JSON only, no other text."""

    try:
        start_time = time.time()
        tracker = get_tracker()
        input_tokens = tracker.estimate_tokens(prompt)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Log token usage
        output_tokens = tracker.estimate_tokens(result_text)
        duration_ms = (time.time() - start_time) * 1000
        tracker.log_usage("command_extract_delete_params", "gpt-4o-mini", input_tokens, output_tokens, duration_ms)
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        extracted = json.loads(result_text)
        print(f"[Extract Delete Params] Extracted: {extracted}")
        return extracted
    except json.JSONDecodeError as e:
        print(f"[Extract Delete Params] JSON decode error: {e}")
        print(f"[Extract Delete Params] Raw response: {result_text[:200]}")
        # Fallback
        return {
            'categories': extract_category_names_from_query(query),
            'reuse_category': detect_reuse_category_in_query(query)
        }
    except Exception as e:
        print(f"[Extract Delete Params] Error: {e}")
        # Fallback
        return {
            'categories': extract_category_names_from_query(query),
            'reuse_category': detect_reuse_category_in_query(query)
        }


async def validate_delete_params(params: Dict[str, Any], guild: discord.Guild) -> Dict[str, Any]:
    """
    Agent 2: Validate and resolve parameters
    
    Returns:
        Dict with validated categories (list of Category objects) and reuse_category, or error message
    """
    validated = {
        'categories': [],
        'reuse_category': False,
        'error': None
    }
    
    # Validate categories
    category_names = params.get('categories', [])
    if not category_names:
        validated['error'] = "❌ No categories specified. Please mention category names like 'Week 1' or 'Playoffs'."
        return validated
    
    if len(category_names) > 5:
        validated['error'] = "❌ Too many categories. You can delete up to 5 categories at once."
        return validated
    
    # Find matching categories
    valid_categories = []
    invalid_categories = []
    
    for cat_name in category_names:
        # Try exact match first
        category = discord.utils.get(guild.categories, name=cat_name)
        if category:
            valid_categories.append(category)
        else:
            # Try case-insensitive match
            for cat in guild.categories:
                if cat and cat.name.lower() == cat_name.lower():
                    valid_categories.append(cat)
                    break
            else:
                invalid_categories.append(cat_name)
    
    if invalid_categories:
        available = [cat.name for cat in guild.categories if cat][:10]
        validated['error'] = (
            f"❌ The following categories don't exist: {', '.join(invalid_categories)}\n\n"
            f"Available categories: {', '.join(available) if available else 'None found'}"
        )
        return validated
    
    if not valid_categories:
        validated['error'] = "❌ No valid categories found to delete."
        return validated
    
    validated['categories'] = valid_categories
    
    # Validate reuse_category (should be boolean)
    reuse_category = params.get('reuse_category', False)
    if isinstance(reuse_category, bool):
        validated['reuse_category'] = reuse_category
    elif isinstance(reuse_category, str):
        validated['reuse_category'] = reuse_category.lower() in ['true', 'yes', '1', 'on']
    else:
        validated['reuse_category'] = False
    
    return validated


def detect_reuse_category_in_query(query: str) -> bool:
    """Detect if category reuse is requested"""
    query_lower = query.lower()
    reuse_keywords = [
        "keep category", "keep categories", "reuse", "keep for future",
        "retain category", "retain categories", "keep the category",
        "keep it", "don't delete category", "keep category name"
    ]
    return any(keyword in query_lower for keyword in reuse_keywords)


def extract_category_names_from_query(query: str) -> list:
    """Extract category names from query - fallback function"""
    import re
    
    query_lower = query.lower()
    categories = []
    
    # Patterns to extract categories
    patterns = [
        r"week\s+(\d+)",  # "Week 1", "week 2"
        r"delete\s+(week\s+\d+)",  # "delete Week 1"
        r"remove\s+(week\s+\d+)",  # "remove Week 1"
        r"clear\s+(week\s+\d+)",  # "clear Week 1"
    ]
    
    # Extract week numbers
    week_matches = re.findall(r"week\s+(\d+)", query_lower)
    for match in week_matches:
        categories.append(f"Week {match}")
    
    # Also look for explicit category names (capitalized words after delete/remove)
    explicit_patterns = [
        r"delete\s+([A-Z][a-zA-Z\s]+?)(?:\s+and|\s*,|\s*$)",
        r"remove\s+([A-Z][a-zA-Z\s]+?)(?:\s+and|\s*,|\s*$)",
    ]
    
    for pattern in explicit_patterns:
        matches = re.findall(pattern, query)
        for match in matches:
            cat_name = match.strip()
            if cat_name and len(cat_name) > 2:
                categories.append(cat_name)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_categories = []
    for cat in categories:
        if cat.lower() not in seen:
            seen.add(cat.lower())
            unique_categories.append(cat)
    
    return unique_categories[:5]  # Limit to 5


async def delete_categories_from_extracted(
    interaction: discord.Interaction,
    categories: list,
    reuse_category: bool
):
    """Delete categories from extracted data"""
    try:
        deleted_channels = []
        deleted_categories = []
        
        for category in categories:
            # Always delete all channels in the category
            for ch in category.channels:
                await ch.delete()
                deleted_channels.append(f"{ch.name} (in {category.name})")
            
            # Delete or retain the category based on user choice
            if reuse_category:
                # Keep the category name but remove all channels
                deleted_categories.append(f"{category.name} (channels deleted, category retained)")
            else:
                # Delete the category completely
                await category.delete()
                deleted_categories.append(f"{category.name} (completely deleted)")
        
        # Create appropriate embed based on what was retained
        if reuse_category:
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
        
    except Exception as e:
        import traceback
        print(f"[Delete Categories] Error: {e}")
        print(f"[Delete Categories] Traceback: {traceback.format_exc()}")
        await interaction.followup.send(
            f"❌ Error deleting categories: {str(e)[:150]}",
            ephemeral=True
        )


# ============================================================================
# TAG USERS AGENTIC SYSTEM
# ============================================================================

async def execute_tag_users(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[str]:
    """Execute /matchups tag-users - tag users in matchup channels"""
    try:
        # Check if user is commissioner
        if not is_commissioner(message.author, server_id):
            return "🚫 You must be a commissioner to tag users in matchups."
        
        if not message.guild:
            return "⚠️ This command can only be used in a server."
        
        # Extract category name from query
        category_name = extract_category_name_from_query(query)
        
        if not category_name:
            # Try to extract from context or ask user
            available_categories = [cat.name for cat in message.guild.categories if cat][:10]
            return (
                f"❌ Please specify a category name. For example: 'Tag users in Week 1'\n\n"
                f"Available categories: {', '.join(available_categories) if available_categories else 'None found'}"
            )
        
        # Validate category exists
        category = discord.utils.get(message.guild.categories, name=category_name)
        if not category:
            # Try case-insensitive
            for cat in message.guild.categories:
                if cat and cat.name.lower() == category_name.lower():
                    category = cat
                    category_name = cat.name  # Use exact name
                    break
        
        if not category:
            available_categories = [cat.name for cat in message.guild.categories if cat][:10]
            return (
                f"❌ Category '{category_name}' not found.\n\n"
                f"Available categories: {', '.join(available_categories) if available_categories else 'None found'}"
            )
        
        # Execute the tagging
        await tag_users_from_extracted(message, category, server_id)
        
        # Return None so the conversation handler doesn't send another message
        return None
        
    except Exception as e:
        import traceback
        print(f"[Tag Users] Error: {e}")
        print(f"[Tag Users] Traceback: {traceback.format_exc()}")
        return f"⚠️ Error tagging users: {str(e)[:150]}"


async def tag_users_from_extracted(
    message: discord.Message,
    category: discord.CategoryChannel,
    server_id: str
):
    """Tag users in matchup channels from extracted category"""
    try:
        from utils.utils import get_db_connection, clean_team_key, format_team_name
        
        # Send processing message
        processing_msg = await message.channel.send("🔄 Tagging users in matchup channels...")
        
        guild = message.guild
        conn = get_db_connection("teams")
        cursor = conn.cursor()
        
        # Special case mappings
        special_mapping = {
            "texas-am": "texas a&m"
        }
        
        status_suffixes = {"✅", "🎲", "☑️"}
        tagged_count = 0
        skipped_count = 0
        
        for channel in category.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            
            # Remove status suffix
            base_name = channel.name
            for emoji in status_suffixes:
                if base_name.endswith(f"-{emoji}"):
                    base_name = base_name[:-(len(emoji) + 1)]
                    break
            
            if "-vs-" not in base_name:
                skipped_count += 1
                continue
            
            raw_team1, raw_team2 = base_name.split("-vs-")
            team1_key = clean_team_key(raw_team1)
            team2_key = clean_team_key(raw_team2)
            
            # Handle special mappings
            if team1_key in special_mapping:
                team1_key = special_mapping[team1_key]
            if team2_key in special_mapping:
                team2_key = special_mapping[team2_key]
            
            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)
            
            # Fetch user IDs from the DB (try CFB, then NFL)
            cursor.execute(
                "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                (team1_key.lower(), server_id)
            )
            user1 = cursor.fetchone()
            if not user1:
                cursor.execute(
                    "SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team1_key.lower(), server_id)
                )
                user1 = cursor.fetchone()
            
            cursor.execute(
                "SELECT user_id FROM cfb_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                (team2_key.lower(), server_id)
            )
            user2 = cursor.fetchone()
            if not user2:
                cursor.execute(
                    "SELECT user_id FROM nfl_teams WHERE LOWER(team_name) = ? AND server_id = ?",
                    (team2_key.lower(), server_id)
                )
                user2 = cursor.fetchone()
            
            user1_id = user1[0] if user1 else None
            user2_id = user2[0] if user2 else None
            
            # Send message
            if user1_id and user2_id:
                await channel.send(f"**{pretty_team1} vs {pretty_team2}**\n\n<@{user1_id}>\n<@{user2_id}>")
                tagged_count += 1
            elif user1_id:
                await channel.send(f"**{pretty_team1} vs CPU ({pretty_team2})**\n\n<@{user1_id}>")
                tagged_count += 1
            elif user2_id:
                await channel.send(f"**{pretty_team1} vs {pretty_team2}**\n\nCPU ({pretty_team1})\n<@{user2_id}>")
                tagged_count += 1
            else:
                skipped_count += 1
        
        # Delete processing message and send success
        try:
            await processing_msg.delete()
        except:
            pass
        
        embed = discord.Embed(
            title="✅ Users Tagged in Matchup Channels",
            description=f"Tagged users in **{category.name}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Results",
            value=f"✅ {tagged_count} matchup channel(s) tagged\n⚠️ {skipped_count} channel(s) skipped (no matchup format or no users)",
            inline=False
        )
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        import traceback
        print(f"[Tag Users] Error: {e}")
        print(f"[Tag Users] Traceback: {traceback.format_exc()}")
        await message.channel.send(
            f"❌ Error tagging users: {str(e)[:150]}"
        )


# ============================================================================
# ANNOUNCE ADVANCE AGENTIC SYSTEM
# ============================================================================

async def execute_announce_advance(
    bot,
    message: discord.Message,
    query: str,
    server_id: str
) -> Optional[str]:
    """Execute /message announce-advance - announce week advance"""
    try:
        # Check if user is commissioner
        if not is_commissioner(message.author, server_id):
            return "🚫 You must be a commissioner to announce advances."
        
        if not message.guild:
            return "⚠️ This command can only be used in a server."
        
        # Agent 1: Extract parameters from natural language
        extracted_params = await extract_announce_advance_params(query, message.guild)
        
        # Agent 2: Validate and resolve parameters
        validated_params = await validate_announce_advance_params(extracted_params, message.guild)
        
        if validated_params.get('error'):
            return validated_params['error']
        
        week = validated_params['week']
        next_advance = validated_params['next_advance']
        mention_roles = validated_params['mention_roles']
        channels = validated_params['channels']
        custom_message = validated_params.get('custom_message', '')
        
        # Create preview embed
        role_mentions_str = " ".join([role.mention for role in mention_roles]) if mention_roles else "None"
        channel_list = "\n".join([f"• {ch.name}" for ch in channels]) if channels else "None"
        
        preview_embed = discord.Embed(
            title="📣 Advance Announcement Preview",
            description="Review the announcement details before sending:",
            color=discord.Color.blue()
        )
        
        preview_embed.add_field(name="Week", value=week, inline=True)
        preview_embed.add_field(name="Next Advance", value=next_advance, inline=True)
        preview_embed.add_field(name="Roles to Mention", value=role_mentions_str or "None", inline=False)
        preview_embed.add_field(name="Channels", value=channel_list or "None", inline=False)
        if custom_message:
            preview_embed.add_field(name="Custom Message", value=custom_message, inline=False)
        
        # Create confirmation view
        from discord import ui, ButtonStyle
        
        class ConfirmAnnounceAdvanceView(ui.View):
            def __init__(self, original_user, week, next_advance, mention_roles, channels, custom_message):
                super().__init__(timeout=300)  # 5 minute timeout
                self.original_user = original_user
                self.week = week
                self.next_advance = next_advance
                self.mention_roles = mention_roles
                self.channels = channels
                self.custom_message = custom_message
                self.confirmed = False
            
            @ui.button(label="✅ Send Announcement", style=ButtonStyle.success)
            async def confirm(self, interaction: discord.Interaction, button: ui.Button):
                if interaction.user.id != self.original_user.id:
                    await interaction.response.send_message("Only the original user can confirm this.", ephemeral=True)
                    return
                
                self.confirmed = True
                # Defer the response so we can send followup messages
                await interaction.response.defer(thinking=True)
                
                # Edit the message to show we're sending
                try:
                    await interaction.edit_original_response(
                        content="Sending announcement...", 
                        embed=None, 
                        view=None
                    )
                except:
                    pass
                
                # Send the announcement
                await announce_advance_from_extracted(
                    interaction,
                    self.week,
                    self.next_advance,
                    self.mention_roles,
                    self.channels,
                    self.custom_message
                )
                self.stop()
            
            @ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: ui.Button):
                await interaction.response.edit_message(
                    content="Announcement cancelled.", 
                    embed=None, 
                    view=None
                )
                self.stop()
        
        view = ConfirmAnnounceAdvanceView(
            message.author,
            week,
            next_advance,
            mention_roles,
            channels,
            custom_message
        )
        
        preview_msg = await message.channel.send(embed=preview_embed, view=view)
        
        # Return None so the conversation handler doesn't send another message
        return None
        
    except Exception as e:
        import traceback
        print(f"[Announce Advance] Error: {e}")
        print(f"[Announce Advance] Traceback: {traceback.format_exc()}")
        return f"⚠️ Error processing announcement: {str(e)[:150]}"


async def extract_announce_advance_params(query: str, guild: discord.Guild) -> Dict[str, Any]:
    """
    Agent 1: Extract parameters from natural language query
    
    Returns:
        Dict with week, next_advance, mention_roles, channels, custom_message
    """
    if not client:
        # Fallback to simple extraction
        return {
            'week': extract_week_from_query(query),
            'next_advance': extract_advance_time_from_query(query),
            'mention_roles': extract_roles_from_query(query),
            'channels': extract_channels_from_query(query, guild),
            'custom_message': extract_custom_message_from_query(query)
        }
    
    # Get available roles and channels for context
    available_roles = [role.name for role in guild.roles if role.name != "@everyone"][:15]
    available_channels = [ch.name for ch in guild.text_channels][:15]
    
    prompt = f"""Extract parameters from this user query about announcing a week advance:

Query: "{query}"

Extract the following:
1. **week**: The week number or name (e.g., "Week 1", "1", "Playoffs")
   - Look for: "week 1", "week 2", "week X", "playoffs", "championship"
   - If just a number, format as "Week N"
   - Return the week identifier

2. **next_advance**: The next advance time (e.g., "Monday at 8 PM", "Friday 3:00 PM EST")
   - Look for: "next advance", "advance time", "advance is", "next advance is"
   - Extract the time/date mentioned
   - Return the advance time string

3. **mention_roles**: Comma-separated list of role names to mention
   - Look for: "mention", "notify", "@role", role names
   - Available roles: {', '.join(available_roles[:10])}
   - Return comma-separated role names or empty string

4. **channels**: List of channel names to send to (up to 5)
   - Look for: "in channel", "to channel", "send to", channel names
   - Available channels: {', '.join(available_channels[:10])}
   - Return as JSON array of channel names

5. **custom_message**: Optional custom message to include
   - Look for: "custom message", "add", "also say", "include"
   - Return the custom message text or empty string

Return ONLY a JSON object with these fields:
{{
    "week": "Week 1" or "1" or "Playoffs",
    "next_advance": "Monday at 8 PM" or "",
    "mention_roles": "Commish,Admin" or "",
    "channels": ["general", "announcements"] or [],
    "custom_message": "Good luck everyone!" or ""
}}

Examples:
- "Announce Week 1, next advance is Monday at 8 PM, mention Commish role, send to general channel"
  → {{"week": "Week 1", "next_advance": "Monday at 8 PM", "mention_roles": "Commish", "channels": ["general"], "custom_message": ""}}

- "Post advance for Week 2, next advance Friday 3 PM, notify @Commish and @Admin, channels general and announcements"
  → {{"week": "Week 2", "next_advance": "Friday 3 PM", "mention_roles": "Commish,Admin", "channels": ["general", "announcements"], "custom_message": ""}}

Return JSON only, no other text."""

    try:
        start_time = time.time()
        tracker = get_tracker()
        input_tokens = tracker.estimate_tokens(prompt)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Log token usage
        output_tokens = tracker.estimate_tokens(result_text)
        duration_ms = (time.time() - start_time) * 1000
        tracker.log_usage("command_extract_announce_params", "gpt-4o-mini", input_tokens, output_tokens, duration_ms)
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        extracted = json.loads(result_text)
        print(f"[Extract Announce Advance Params] Extracted: {extracted}")
        return extracted
    except json.JSONDecodeError as e:
        print(f"[Extract Announce Advance Params] JSON decode error: {e}")
        print(f"[Extract Announce Advance Params] Raw response: {result_text[:200]}")
        # Fallback
        return {
            'week': extract_week_from_query(query),
            'next_advance': extract_advance_time_from_query(query),
            'mention_roles': extract_roles_from_query(query),
            'channels': extract_channels_from_query(query, guild),
            'custom_message': extract_custom_message_from_query(query)
        }
    except Exception as e:
        print(f"[Extract Announce Advance Params] Error: {e}")
        # Fallback
        return {
            'week': extract_week_from_query(query),
            'next_advance': extract_advance_time_from_query(query),
            'mention_roles': extract_roles_from_query(query),
            'channels': extract_channels_from_query(query, guild),
            'custom_message': extract_custom_message_from_query(query)
        }


async def validate_announce_advance_params(params: Dict[str, Any], guild: discord.Guild) -> Dict[str, Any]:
    """
    Agent 2: Validate and resolve parameters
    
    Returns:
        Dict with validated parameters or error message
    """
    validated = {
        'week': None,
        'next_advance': None,
        'mention_roles': [],
        'channels': [],
        'custom_message': '',
        'error': None
    }
    
    # Validate week
    week = params.get('week', '')
    if not week or not week.strip():
        validated['error'] = "❌ Please specify a week (e.g., 'Week 1' or '1')."
        return validated
    
    # Format week intelligently
    week_str = week.strip()
    if week_str.isdigit():
        validated['week'] = f"Week {week_str}"
    else:
        validated['week'] = week_str
    
    # Validate next_advance (required)
    next_advance = params.get('next_advance', '')
    if not next_advance or not next_advance.strip():
        validated['error'] = "❌ Please specify the next advance time (e.g., 'Monday at 8 PM')."
        return validated
    validated['next_advance'] = next_advance.strip()
    
    # Validate mention_roles (required)
    mention_roles_str = params.get('mention_roles', '')
    if mention_roles_str:
        role_names = [r.strip() for r in mention_roles_str.split(',')]
        valid_roles = []
        invalid_roles = []
        
        for role_name in role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                valid_roles.append(role)
            else:
                invalid_roles.append(role_name)
        
        if invalid_roles:
            available = [r.name for r in guild.roles if r.name != '@everyone'][:10]
            validated['error'] = (
                f"❌ The following roles don't exist: {', '.join(invalid_roles)}\n\n"
                f"Available roles: {', '.join(available)}"
            )
            return validated
        
        validated['mention_roles'] = valid_roles
    else:
        validated['error'] = "❌ Please specify at least one role to mention (e.g., 'Commish' or 'Admin')."
        return validated
    
    # Validate channels (required, at least one)
    channel_names = params.get('channels', [])
    if not channel_names:
        validated['error'] = "❌ Please specify at least one channel to send the announcement to."
        return validated
    
    if len(channel_names) > 5:
        validated['error'] = "❌ Too many channels. You can send to up to 5 channels."
        return validated
    
    valid_channels = []
    invalid_channels = []
    
    for channel_name in channel_names:
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel:
            valid_channels.append(channel)
        else:
            invalid_channels.append(channel_name)
    
    if invalid_channels:
        available = [ch.name for ch in guild.text_channels][:10]
        validated['error'] = (
            f"❌ The following channels don't exist: {', '.join(invalid_channels)}\n\n"
            f"Available channels: {', '.join(available)}"
        )
        return validated
    
    if not valid_channels:
        validated['error'] = "❌ No valid channels found."
        return validated
    
    validated['channels'] = valid_channels
    
    # Custom message is optional
    validated['custom_message'] = params.get('custom_message', '').strip()
    
    return validated


def extract_week_from_query(query: str) -> str:
    """Extract week from query - fallback function"""
    import re
    
    query_lower = query.lower()
    
    # Look for "week X" pattern
    week_match = re.search(r'week\s+(\d+)', query_lower)
    if week_match:
        return f"Week {week_match.group(1)}"
    
    # Look for just a number
    number_match = re.search(r'\b(\d+)\b', query)
    if number_match:
        return f"Week {number_match.group(1)}"
    
    # Look for playoffs, championship, etc.
    if "playoff" in query_lower:
        return "Playoffs"
    if "championship" in query_lower or "champ" in query_lower:
        return "Championship"
    
    return ""


def extract_advance_time_from_query(query: str) -> str:
    """Extract advance time from query - fallback function"""
    import re
    
    query_lower = query.lower()
    
    # Look for patterns like "next advance is X", "advance time X", "advance X"
    patterns = [
        r"next advance is (.+?)(?:,|$|\.|and|to)",
        r"advance time (.+?)(?:,|$|\.|and|to)",
        r"advance is (.+?)(?:,|$|\.|and|to)",
        r"next advance (.+?)(?:,|$|\.|and|to)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(1).strip()
    
    return ""


def extract_channels_from_query(query: str, guild: discord.Guild) -> list:
    """Extract channel names from query - fallback function"""
    import re
    
    query_lower = query.lower()
    channels = []
    
    # Look for "in channel X", "to channel X", "send to X"
    patterns = [
        r"(?:in|to|send to)\s+channel\s+([a-z0-9\-_]+)",
        r"channel[s]?\s+([a-z0-9\-_]+)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, query_lower)
        for match in matches:
            if match and match not in channels:
                channels.append(match)
    
    # Also check if any channel names from the server appear in the query
    for channel in guild.text_channels:
        if channel.name.lower() in query_lower:
            if channel.name not in channels:
                channels.append(channel.name)
    
    return channels[:5]  # Limit to 5


def extract_custom_message_from_query(query: str) -> str:
    """Extract custom message from query - fallback function"""
    import re
    
    # Look for phrases like "also say", "add", "custom message", "include"
    patterns = [
        r"also say (.+?)(?:$|\.)",
        r"add (.+?)(?:$|\.)",
        r"custom message (.+?)(?:$|\.)",
        r"include (.+?)(?:$|\.)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            return match.group(1).strip()
    
    return ""


async def announce_advance_from_extracted(
    interaction: discord.Interaction,
    week: str,
    next_advance: str,
    mention_roles: list,
    channels: list,
    custom_message: str
):
    """Send advance announcement from extracted data"""
    try:
        # Build role mentions
        role_mentions = " ".join([role.mention for role in mention_roles])
        
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
        
        sent_channels = []
        failed_channels = []
        
        for channel in channels:
            try:
                await channel.send(role_mentions, embed=embed)
                sent_channels.append(channel.name)
            except Exception as e:
                print(f"[Announce Advance] Failed to send to {channel.name}: {e}")
                failed_channels.append(channel.name)
        
        # Send success message
        result_embed = discord.Embed(
            title="✅ Advance Announcement Sent",
            description=f"Announcement for **{display_week}** has been sent.",
            color=discord.Color.green()
        )
        
        if sent_channels:
            result_embed.add_field(
                name="✅ Sent To",
                value="\n".join([f"• {ch}" for ch in sent_channels]),
                inline=False
            )
        
        if failed_channels:
            result_embed.add_field(
                name="❌ Failed To Send",
                value="\n".join([f"• {ch}" for ch in failed_channels]),
                inline=False
            )
        
        await interaction.followup.send(embed=result_embed, ephemeral=False)
        
    except Exception as e:
        import traceback
        print(f"[Announce Advance] Error: {e}")
        print(f"[Announce Advance] Traceback: {traceback.format_exc()}")
        await interaction.followup.send(
            f"❌ Error sending announcement: {str(e)[:150]}",
            ephemeral=True
        )


async def execute_request_history(viewer_id: int, server_id: str, target_user_id: int) -> str:
    """Execute /attributes history"""
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT request_number, player, attribute, amount, status
                FROM attribute_requests
                WHERE user_id = ? AND server_id = ?
                ORDER BY request_number DESC
                LIMIT 10
            """, (target_user_id, server_id))
            records = cursor.fetchall()
        
        if not records:
            if target_user_id == viewer_id:
                return "📭 You have no upgrade request history yet."
            else:
                return f"📭 <@{target_user_id}> has no request history."
        
        status_emojis = {
            "approved": "✅",
            "denied": "❌",
            "pending": "⏳"
        }
        
        lines = [f"📚 **Attribute Request History for <@{target_user_id}>:**"]
        for req_id, player, attr, amt, status in records:
            emoji = status_emojis.get(status.lower(), "")
            lines.append(f"• `#{req_id}` `{attr}` → **{player}** for **{amt}pt(s)** — {emoji} `{status.capitalize()}`")
        
        return "\n".join(lines)
    except Exception as e:
        return "⚠️ Couldn't check request history. Try using `/attributes history` instead."


async def execute_list_matchups(guild: discord.Guild, category_name: str, server_id: str) -> str:
    """Execute /matchups list-all"""
    try:
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            return f"❌ No category named '{category_name}' found."
        
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
            return "📭 No matchup channels found in that category."
        
        lines = [f"🆚 **Matchups in {category_name}**\n"]
        
        for ch, raw_name, emoji in matchup_channels:
            team1_raw, team2_raw = raw_name.split("-vs-")
            team1_key = clean_team_key(team1_raw)
            team2_key = clean_team_key(team2_raw)
            
            pretty_team1 = format_team_name(team1_key)
            pretty_team2 = format_team_name(team2_key)
            
            # Get user assignments
            league_type = get_server_setting(server_id, "league_type") or "cfb"
            teams_table = "nfl_teams" if league_type.lower() == "nfl" else "cfb_teams"
            
            cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team1_key.lower(), server_id))
            user1 = cursor.fetchone()
            cursor.execute(f"SELECT user_id FROM {teams_table} WHERE LOWER(team_name) = ? AND server_id = ?", (team2_key.lower(), server_id))
            user2 = cursor.fetchone()
            
            user1_mention = f"<@{user1[0]}>" if user1 else "CPU"
            user2_mention = f"<@{user2[0]}>" if user2 else "CPU"
            
            emoji_str = f" {emoji}" if emoji else ""
            lines.append(f"**{pretty_team1}** vs **{pretty_team2}**\n{user1_mention} vs {user2_mention}{emoji_str}\n")
        
        conn.close()
        
        result = "".join(lines)
        if len(result) > 1900:
            result = "".join(lines[:15])
            result += f"\n... and {len(matchup_channels) - 15} more matchups. Use `/matchups list-all category_name:{category_name}` to see all."
        
        return result
    except Exception as e:
        return f"⚠️ Couldn't list matchups. Try using `/matchups list-all category_name:{category_name}` instead."


async def execute_check_user_points(guild: discord.Guild, user_id: int, server_id: str) -> str:
    """Execute /attributes check-user (commissioner only)"""
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user_id, server_id)
            )
            row = cursor.fetchone()
        
        available = row[0] if row else 0
        user = guild.get_member(user_id)
        user_display = user.display_name if user else f"<@{user_id}>"
        
        return f"🔍 **{user_display}** currently has **{available} attribute point{'s' if available != 1 else ''}** available."
    except Exception as e:
        return "⚠️ Couldn't check user points. Try using `/attributes check-user` instead."


async def execute_check_all_points(guild: discord.Guild, server_id: str) -> str:
    """Execute /attributes check-all (commissioner only)"""
    try:
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, available
                FROM attribute_points
                WHERE server_id = ?
                ORDER BY available DESC
            """, (server_id,))
            records = cursor.fetchall()
        
        if not records:
            return "📭 No users have points recorded yet."
        
        lines = ["📋 **All Users' Available Attribute Points:**"]
        for user_id, available in records:
            member = guild.get_member(user_id)
            name = member.display_name if member else f"<@{user_id}>"
            lines.append(f"• {name}: **{available}pt{'s' if available != 1 else ''}**")
        
        result = "\n".join(lines)
        if len(result) > 1900:
            result = "\n".join(lines[:30])
            result += f"\n\n... and {len(records) - 30} more users. Use `/attributes check-all` to see all."
        
        return result
    except Exception as e:
        return "⚠️ Couldn't check all points. Try using `/attributes check-all` instead."


async def execute_view_settings(guild: discord.Guild, server_id: str) -> str:
    """Execute /settings view (commissioner only)"""
    try:
        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting, new_value FROM server_settings
                WHERE server_id = ?
            """, (server_id,))
            settings = cursor.fetchall()
        
        if not settings:
            return "⚙️ This server has no custom settings yet."
        
        lines = ["⚙️ **Server Settings:**\n"]
        for setting, value in settings:
            if setting == "record_tracking_enabled":
                display_value = "✅ ON" if value.lower() == "on" else "❌ OFF"
            elif setting == "league_type":
                display_value = value.upper()
            elif setting == "stream_announcements_enabled":
                display_value = "✅ ON" if value.lower() == "on" else "❌ OFF"
            elif setting in {"attributes_log_channel", "stream_watch_channel"}:
                channel = guild.get_channel(int(value))
                display_value = channel.mention if channel else f"Channel ID: {value}"
            else:
                display_value = value
            
            lines.append(f"• **{setting}**: {display_value}")
        
        return "\n".join(lines)
    except Exception as e:
        return "⚠️ Couldn't view settings. Try using `/settings view` instead."


def extract_user_mention(message: discord.Message, query: str) -> Optional[discord.Member]:
    """Extract user mention from query"""
    import re
    
    # Check for @mentions in the message
    if message.mentions:
        return message.mentions[0]
    
    # Check for user ID in query
    user_id_match = re.search(r'<@!?(\d+)>', query)
    if user_id_match:
        user_id = int(user_id_match.group(1))
        return message.guild.get_member(user_id)
    
    # Try to find username in query (simple heuristic)
    query_lower = query.lower()
    for member in message.guild.members:
        if member.display_name.lower() in query_lower or member.name.lower() in query_lower:
            return member
    
    return None


def extract_category_name(query: str) -> Optional[str]:
    """Extract category name from query"""
    import re
    
    query_lower = query.lower()
    
    # Patterns to extract category
    patterns = [
        r"matchups in (.+)",
        r"matchups for (.+)",
        r"list matchups (.+)",
        r"show matchups (.+)",
        r"week (\d+)",
        r"category (.+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            category = match.group(1).strip()
            # Remove common trailing words
            category = re.sub(r'\s+(matchups|category|week)$', '', category)
            if category and len(category) > 2:
                # If it's just a number, format as "Week N"
                if category.isdigit():
                    return f"Week {category}"
                return category.title()
    
    # Check for "this week" or "current week"
    if "this week" in query_lower or "current week" in query_lower:
        # We'll need to find the most recent week category
        # For now, return None and let the matchup query handler deal with it
        return None
    
    return None

