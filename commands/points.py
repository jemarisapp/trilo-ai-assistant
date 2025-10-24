# File: commands/points.py

import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, Interaction
from enum import Enum
from utils.utils import get_db_connection
from utils.common import commissioner_only, subscription_required, PRO_SKUS
from utils.command_logger import log_command
from discord import Interaction

ATTRIBUTE_CHOICES = [
    ("Speed", "SPD"), ("Strength", "STR"), ("Agility", "AGI"), ("Acceleration", "ACC"), ("Awareness", "AWR"),
    ("Stamina", "STA"), ("Injury", "INJ"), ("Toughness", "TGH"), ("Throw Power", "THP"),
    ("Short Throw Accuracy", "SAC"), ("Medium Throw Accuracy", "MAC"), ("Deep Throw Accuracy", "DAC"),
    ("Throw On The Run", "RUN"), ("Throw Under Pressure", "TUP"), ("Break Sack", "BSK"), ("Play Action", "PAC"),
    ("Break Tackle", "BTK"), ("Trucking", "TRK"), ("Change of Direction", "COD"), ("Ball Carrier Vision", "BCV"),
    ("Stiff Arm", "SFA"), ("Spin Move", "SPM"), ("Juke Move", "JKM"), ("Carrying", "CAR"), ("Catching", "CTH"),
    ("Short Route Run", "SRR"), ("Medium Route Run", "MRR"), ("Deep Route Run", "DRR"), ("Catch in Traffic", "CIT"),
    ("Spectacular Catch", "SPC"), ("Release", "RLS"), ("Jumping", "JMP"), ("Return", "RET"), ("Tackle", "TAK"),
    ("Hit Power", "POW"), ("Power Moves", "PMV"), ("Finesse Moves", "FMV"), ("Block Shedding", "BSH"),
    ("Pursuit", "PUR"), ("Play Recognition", "PRC"), ("Man Coverage", "MCV"), ("Zone Coverage", "ZCV"),
    ("Press", "PRS"), ("Pass Block", "PBK"), ("Pass Block Power", "PBP"), ("Pass Block Finesse", "PBF"),
    ("Run Block", "RBK"), ("Run Block Power", "RBP"), ("Run Block Finesse", "RBF"), ("Lead Block", "LBK"),
    ("Impact Blocking", "IBL"), ("Kick Power", "KPW"), ("Kick Accuracy", "KAC")
]


def test_database_connection(database_name: str) -> bool:
    """Test if a database connection can be established"""
    try:
        with get_db_connection(database_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
    except Exception as e:
        print(f"[database_test] Failed to connect to {database_name}: {e}")
        return False

def log_points_action(interaction: discord.Interaction, title: str, description: str, color: discord.Color):
    server_id = str(interaction.guild.id)
    try:
        # Test database connection first
        if not test_database_connection("keys"):
            print(f"[attributes_log] Cannot connect to keys database for server {server_id}")
            return None
            
        with get_db_connection("keys") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT new_value FROM server_settings
                WHERE server_id = ? AND setting = 'attributes_log_channel'
            """, (server_id,))
            row = cursor.fetchone()

        if row:
            log_channel = interaction.guild.get_channel(int(row[0]))
            if log_channel:
                embed = discord.Embed(title=title, description=description, color=color)
                embed.set_footer(text=f"Trilo • The Dynasty League Assistant")
                return log_channel.send(embed=embed)
            else:
                print(f"[attributes_log] Log channel not found for server {server_id}")
        else:
            print(f"[attributes_log] No log channel configured for server {server_id}")
    except Exception as e:
        print(f"[attributes_log] Failed to log action: {e}")

class ConfirmClearAllPointsView(ui.View):
    def __init__(self, interaction: Interaction, server_id: str):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.server_id = server_id

    @ui.button(label="Yes, Clear All", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to confirm this.", ephemeral=True)
            return

        try:
            with get_db_connection("attributes") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attribute_points WHERE server_id = ?", (self.server_id,))
                conn.commit()

            await interaction.response.edit_message(
                content="🧹 All attribute points have been cleared for this server.",
                view=None
            )

            await log_points_action(
                interaction,
                "🧹 Attribute Points Cleared",
                f"All points were cleared by {interaction.user.mention}.",
                discord.Color.orange()
            )
        except Exception as e:
            print(f"[clear_all_points] Error: {e}")
            await interaction.response.edit_message("⚠️ Failed to clear points.", view=None)

        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("You are not authorized to cancel this.", ephemeral=True)
            return

        await interaction.response.edit_message(content="Cancelled. No points were cleared.", view=None)
        self.stop()



def setup_points_commands(bot: commands.Bot):
    attributes_group = app_commands.Group(name="attributes", description="Attribute points system")

    def update_points_balance(user_id: int, server_id: str, amount: int):
        try:
            with get_db_connection("attributes") as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT available, total_earned FROM attribute_points WHERE user_id = ? AND server_id = ?",
                    (user_id, server_id)
                )
                result = cursor.fetchone()

                if result:
                    new_available = result[0] + amount
                    new_total = result[1] + amount
                    cursor.execute(
                        "UPDATE attribute_points SET available = ?, total_earned = ?, last_updated = datetime('now', 'localtime') WHERE user_id = ? AND server_id = ?",
                        (new_available, new_total, user_id, server_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO attribute_points (user_id, server_id, available, total_earned, created_at, last_updated) VALUES (?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))",
                        (user_id, server_id, amount, amount)
                    )
                conn.commit()
                print(f"[update_points_balance] Successfully updated points for user {user_id}: +{amount}")
                return True
        except Exception as e:
            print(f"[update_points_balance] Error updating points for user {user_id}: {e}")
            return False

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="give", description="Give attribute points to users.")
    @app_commands.describe(
        users="Mention users with @",
        amount="Amount of points to award to each user.",
        reason="Why are you giving these points?",
        note="(Optional) Add a note about upgrade rules or limits."
    )
    @log_command("attributes give")
    async def give_points(interaction: discord.Interaction, users: str, amount: int, reason: str, note: str = ""):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        # Test database connections before proceeding
        if not test_database_connection("attributes"):
            await interaction.response.send_message("⚠️ Database connection error. Please contact an administrator.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        server_id = str(interaction.guild.id)
        mentions = users.split()
        successes = []
        failures = []

        for entry in mentions:
            member = None
            try:
                if entry.startswith("<@") and entry.endswith(">"):
                    # Handle both <@123456789> and <@!123456789> formats
                    user_id_str = entry.replace("<@", "").replace("!", "").replace(">", "")
                    if user_id_str.isdigit():
                        user_id = int(user_id_str)
                        member = interaction.guild.get_member(user_id)
                elif entry.isdigit():
                    member = interaction.guild.get_member(int(entry))

                if member:
                    # Update points and check if successful
                    if update_points_balance(member.id, server_id, amount):
                        # Log to attributes_log only if points were successfully updated
                        try:
                            with get_db_connection("attributes") as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at) VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))",
                                    (member.id, server_id, amount, reason, interaction.user.id)
                                )
                                conn.commit()
                                print(f"[give_points] Logged points for user {member.id}: +{amount}")
                        except Exception as e:
                            print(f"[give_points] Failed to log to attributes_log for user {member.id}: {e}")
                        
                        # Verify points were actually stored
                        try:
                            with get_db_connection("attributes") as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                                    (member.id, server_id)
                                )
                                verification = cursor.fetchone()
                                if verification and verification[0] >= amount:
                                    print(f"[give_points] Verification successful for user {member.id}: {verification[0]} points available")
                                    successes.append(member.mention)
                                    
                                    # Send DM notification to the user
                                    try:
                                        dm_embed = discord.Embed(
                                            title="🎁 Attribute Points Received!",
                                            description=f"You have received **{amount} attribute point{'s' if amount != 1 else ''}**!",
                                            color=discord.Color.from_rgb(243, 170, 7)
                                        )
                                        dm_embed.add_field(name="Total Available", value=f"{verification[0]}pt(s)", inline=True)
                                        dm_embed.add_field(name="Given By", value=interaction.user.display_name, inline=True)
                                        dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                                        dm_embed.add_field(name="Reason", value=reason, inline=False)
                                        dm_embed.add_field(name="", value="", inline=False)  # Spacing
                                        dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                                        dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                                        
                                        await member.send(embed=dm_embed)
                                        print(f"[give_points] DM sent to user {member.id} for {amount} points received")
                                    except Exception as e:
                                        print(f"[give_points] Failed to send DM to user {member.id}: {e}")
                                    
                                else:
                                    print(f"[give_points] Verification failed for user {member.id}: expected at least {amount}, got {verification[0] if verification else 'None'}")
                                    failures.append(f"{member.mention} (verification failed)")
                        except Exception as e:
                            print(f"[give_points] Verification error for user {member.id}: {e}")
                            failures.append(f"{member.mention} (verification error)")
                    else:
                        failures.append(f"{entry} (points update failed)")
                else:
                    failures.append(entry)
            except Exception as e:
                print(f"[give_points] Error processing entry '{entry}': {e}")
                failures.append(f"{entry} (parsing error)")

        result = f"✅ **{amount} points** given to: {', '.join(successes)}\n\n"
        if failures:
            result += f"❌ Could not find: {', '.join(failures)}\n\n"
        result += f"📌 **{reason}**\n\n"
        result += f"📝 *Click to copy the command below, then paste it in your league's chat to request an upgrade:*\n`/attributes request`"
        if note:
            result += f"\n\n✏️ **Commissioner Note:** {note}"

        await interaction.followup.send(result)

        # Log to configured channel only if there were successful point distributions
        if successes:
            log_description = f"**By:** {interaction.user.mention}\n**Amount:** {amount}\n**Reason:** {reason}"
            log_description += f"\n**Recipients:** {', '.join(successes)}"
            if note:
                log_description += f"\n**Note:** {note}"

            await log_points_action(
                interaction,
                "➕ Attribute Points Given",
                log_description,
                discord.Color.from_rgb(243, 170, 7)
            )
        else:
            print(f"[give_points] No successful point distributions to log for server {server_id}")

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="give-role", description="Give attribute points to all members of a specific role.")
    @app_commands.describe(
        role="The role whose members will receive points.",
        amount="Amount of points to award to each role member.",
        reason="Why are you giving these points?",
        note="(Optional) Add a note about upgrade rules or limits."
    )
    @log_command("attributes give-role")
    async def give_points_to_role(interaction: discord.Interaction, role: discord.Role, amount: int, reason: str, note: str = ""):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        # Test database connections before proceeding
        if not test_database_connection("attributes"):
            await interaction.response.send_message("⚠️ Database connection error. Please contact an administrator.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        server_id = str(interaction.guild.id)
        
        # Get all members with this role
        role_members = [member for member in role.members if not member.bot]
        
        if not role_members:
            await interaction.followup.send(f"❌ No human members found in the {role.mention} role.", ephemeral=True)
            return

        successes = []
        failures = []
        total_members = len(role_members)

        # Process each role member
        for member in role_members:
            try:
                # Update points and check if successful
                if update_points_balance(member.id, server_id, amount):
                    # Log to attributes_log only if points were successfully updated
                    try:
                        with get_db_connection("attributes") as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at) VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))",
                                (member.id, server_id, amount, reason, interaction.user.id)
                            )
                            conn.commit()
                            print(f"[give_points_to_role] Logged points for user {member.id}: +{amount}")
                    except Exception as e:
                        print(f"[give_points_to_role] Failed to log to attributes_log for user {member.id}: {e}")
                    
                    # Verify points were actually stored
                    try:
                        with get_db_connection("attributes") as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                                (member.id, server_id)
                            )
                            verification = cursor.fetchone()
                            if verification and verification[0] >= amount:
                                print(f"[give_points_to_role] Verification successful for user {member.id}: {verification[0]} points available")
                                successes.append(member.mention)
                                
                                # Send DM notification to the user
                                try:
                                    dm_embed = discord.Embed(
                                        title="🎁 Attribute Points Received!",
                                        description=f"You have received **{amount} attribute point{'s' if amount != 1 else ''}**!",
                                        color=discord.Color.from_rgb(243, 170, 7)
                                    )
                                    dm_embed.add_field(name="Total Available", value=f"{verification[0]}pt(s)", inline=True)
                                    dm_embed.add_field(name="Given By", value=interaction.user.display_name, inline=True)
                                    dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                                    dm_embed.add_field(name="", value="", inline=False)  # Spacing
                                    dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                                    dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                                    
                                    await member.send(embed=dm_embed)
                                    print(f"[give_points_to_role] DM sent to user {member.id} for {amount} points received")
                                except Exception as e:
                                    print(f"[give_points_to_role] Failed to send DM to user {member.id}: {e}")
                                
                            else:
                                print(f"[give_points_to_role] Verification failed for user {member.id}: expected at least {amount}, got {verification[0] if verification else 'None'}")
                                failures.append(f"{member.mention} (verification failed)")
                    except Exception as e:
                        print(f"[give_points_to_role] Verification error for user {member.id}: {e}")
                        failures.append(f"{member.mention} (verification error)")
                else:
                    failures.append(f"{member.mention} (points update failed)")
            except Exception as e:
                print(f"[give_points_to_role] Error processing member {member.id}: {e}")
                failures.append(f"{member.mention} (processing error)")

        # Build result message
        result = f"✅ **{amount} points** given to: {role.mention}\n\n"
        
        if failures:
            result += f"❌ **Failed:** {', '.join(failures[:5])}"
            if len(failures) > 5:
                result += f" and {len(failures) - 10} more..."
            result += "\n\n"
        
        result += f"📌 **{reason}**\n\n"
        result += f"📝 *Click to copy the command below, then paste it in your league's chat to request an upgrade:*\n`/attributes request`"
        if note:
            result += f"\n\n✏️ **Commissioner Note:** {note}"

        await interaction.followup.send(result)

        # Log to configured channel only if there were successful point distributions
        if successes:
            log_description = f"**Role:** {role.mention}\n**By:** {interaction.user.mention}\n**Amount:** {amount}\n**Reason:** {reason}\n**Total Recipients:** {len(successes)}"
            if note:
                log_description += f"\n**Note:** {note}"

            await log_points_action(
                interaction,
                "👥 Points Given to Role",
                log_description,
                discord.Color.from_rgb(243, 170, 7)
            )
        else:
            print(f"[give_points_to_role] No successful point distributions to log for role {role.name} in server {server_id}")

    @subscription_required(allowed_skus=PRO_SKUS)
    @attributes_group.command(name="my-points", description="Check your current attribute point balance.")
    @log_command("attributes my-points")
    async def check_points(interaction: discord.Interaction):
        user_id = interaction.user.id
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user_id, server_id)
            )
            row = cursor.fetchone()

        points = row[0] if row else 0
        await interaction.response.send_message(
            f"🧮 You currently have **{points} attribute point{'s' if points != 1 else ''}** available.",
            ephemeral=True
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @attributes_group.command(name="request", description="Submit a request to spend your points.")
    @app_commands.describe(
        player="Position & name of the player you're upgrading.",
        attribute="The attribute you're increasing",
        amount="How many points you want to spend. Type the number only"
    )
    @log_command("attributes request")
    async def request_attribute_upgrade(
        interaction: discord.Interaction,
        player: str,
        attribute: str,
        amount: int
    ):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        # Define valid attribute values (for validation)
        valid_attributes = {f"{name} ({abbr})" for name, abbr in ATTRIBUTE_CHOICES}

        if attribute not in valid_attributes:
            await interaction.response.send_message(
                f"❌ `{attribute}` is not a valid attribute.\nPlease select one from the dropdown menu.",
                ephemeral=True
            )
            return


        user_id = interaction.user.id
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user_id, server_id)
            )
            row = cursor.fetchone()
            available_points = row[0] if row else 0

            if available_points < amount:
                await interaction.response.send_message(
                    f"You only have **{available_points}** points available and can't request to spend {amount}.",
                    ephemeral=True
                )
                return

            cursor.execute("""
                INSERT INTO attribute_requests (
                    user_id, server_id, player, attribute, amount, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', datetime('now', 'localtime'), datetime('now', 'localtime'))
            """, (user_id, server_id, player, attribute, amount))
            request_number = cursor.lastrowid
            conn.commit()

        await interaction.response.send_message(
            f"📨 **Request #{request_number} Submitted**\n"
            f"<@{user_id}> is requesting to spend **{amount} points** to upgrade `{attribute}` for **{player}**.",
            ephemeral=False
        )

        await log_points_action(
            interaction,
            "📨 Attribute Request Submitted",
            f"**User:** {interaction.user.mention}\n**Player:** {player}\n**Attribute:** `{attribute}`\n**Amount:** {amount}pt(s)\n**Request #:** {request_number}",
            discord.Color.blurple()
        )

    @request_attribute_upgrade.autocomplete("attribute")
    async def autocomplete_attribute(interaction: discord.Interaction, current: str):
        current_lower = current.lower()
        return [
            app_commands.Choice(name=f"{name} – {abbr}", value=f"{name} ({abbr})")
            for name, abbr in ATTRIBUTE_CHOICES
            if current_lower in name.lower() or current_lower in abbr.lower()
        ][:25]

    
    
    class Decision(str, Enum):
        approve = "approve"
        deny = "deny"


    # Autocomplete: Get pending request IDs for the server
    @attributes_group.command(name="approve", description="Approve a pending upgrade request.")
    @app_commands.describe(request_number="Select a pending request to approve")
    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @log_command("attributes approve")
    async def approve_request(interaction: Interaction, request_number: int):
        await handle_request_action(interaction, request_number, decision="approve")

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="approve-all", description="Approve all pending upgrade requests.")
    @app_commands.describe(user="Whose requests you want to approve. Leave blank to approve all users.")
    @log_command("attributes approve-all")
    async def approve_all_requests(interaction: Interaction, user: discord.Member = None):
        server_id = str(interaction.guild.id)
        
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            
            # Get all pending requests (filtered by user if specified)
            if user:
                cursor.execute("""
                    SELECT request_number, user_id, amount, player, attribute
                    FROM attribute_requests
                    WHERE status = 'pending' AND server_id = ? AND user_id = ?
                    ORDER BY request_number
                """, (server_id, user.id))
            else:
                cursor.execute("""
                    SELECT request_number, user_id, amount, player, attribute
                    FROM attribute_requests
                    WHERE status = 'pending' AND server_id = ?
                    ORDER BY request_number
                """, (server_id,))
            pending_requests = cursor.fetchall()
            
            if not pending_requests:
                await interaction.response.send_message("📭 No pending requests to approve.", ephemeral=True)
                return
            
            # Check if all users have enough points
            failed_requests = []
            successful_requests = []
            
            for req_id, user_id, amount, player, attribute in pending_requests:
                cursor.execute("SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?", (user_id, server_id))
                available_row = cursor.fetchone()
                available_points = available_row[0] if available_row else 0
                
                if available_points < amount:
                    failed_requests.append((req_id, user_id, player, attribute, amount, available_points))
                else:
                    successful_requests.append((req_id, user_id, player, attribute, amount))
            
            if failed_requests:
                # Show failed requests first
                failed_msg = "⚠️ **Some requests cannot be approved due to insufficient points:**\n"
                for req_id, user_id, player, attribute, amount, available in failed_requests:
                    failed_msg += f"• Request #{req_id}: <@{user_id}> needs {amount}pt for {player} ({attribute}) but only has {available}pt\n"
                
                await interaction.response.send_message(failed_msg, ephemeral=True)
                return
            
            # Process all successful requests
            approved_count = 0
            for req_id, user_id, player, attribute, amount in successful_requests:
                # Update user's available points
                cursor.execute("SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?", (user_id, server_id))
                available_row = cursor.fetchone()
                available_points = available_row[0] if available_row else 0
                new_available = available_points - amount
                
                cursor.execute("UPDATE attribute_points SET available = ? WHERE user_id = ? AND server_id = ?", (new_available, user_id, server_id))
                cursor.execute("UPDATE attribute_requests SET status = 'approved', updated_at = datetime('now', 'localtime') WHERE request_number = ?", (req_id,))
                approved_count += 1
            
            conn.commit()
        
        # Build detailed response message
        if user:
            response_lines = [f"✅ **Approved {approved_count} requests from {user.mention}** successfully!"]
        else:
            response_lines = [f"✅ **Approved {approved_count} requests** successfully!"]
        for req_id, user_id, player, attribute, amount in successful_requests:
            response_lines.append(f"- Request #{req_id} by <@{user_id}> to upgrade {attribute} on {player} for {amount}pt(s) has been approved.")
        
        await interaction.response.send_message(
            "\n".join(response_lines),
            ephemeral=False
        )
        
        # Send DM notifications to all approved users
        for req_id, user_id, player, attribute, amount in successful_requests:
            try:
                user = interaction.guild.get_member(user_id)
                if user:
                    # Get current available points for this user to show remaining
                    with get_db_connection("attributes") as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?", (user_id, server_id))
                        current_available = cursor.fetchone()[0]
                    
                    dm_embed = discord.Embed(
                        title="✅ Attribute Request Approved!",
                        description=f"Your request to upgrade **{attribute}** on **{player}** has been approved!",
                        color=discord.Color.green()
                    )
                    dm_embed.add_field(name="Request #", value=f"#{req_id}", inline=True)
                    dm_embed.add_field(name="Points Spent", value=f"{amount}pt(s)", inline=True)
                    dm_embed.add_field(name="Approved By", value=interaction.user.display_name, inline=True)
                    dm_embed.add_field(name="Total Remaining", value=f"{current_available}pt(s)", inline=True)
                    dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                    dm_embed.add_field(name="", value="", inline=False)  # Spacing
                    dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                    dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                    
                    await user.send(embed=dm_embed)
                    print(f"[approve_all_requests] DM sent to user {user_id} for approved request #{req_id}")
            except Exception as e:
                print(f"[approve_all_requests] Failed to send DM to user {user_id}: {e}")

        await log_points_action(
            interaction,
            "✅ All Attribute Requests Approved",
            f"**Approved:** {approved_count} requests\n**By:** {interaction.user.mention}",
            discord.Color.green()
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="deny-all", description="Deny all pending upgrade requests.")
    @app_commands.describe(
        user="Whose requests you want to deny. Leave blank to deny all users.",
        reason="(Optional) Reason for denying these requests."
    )
    @log_command("attributes deny-all")
    async def deny_all_requests(interaction: Interaction, user: discord.Member = None, reason: str = "No reason provided"):
        server_id = str(interaction.guild.id)
        
        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            
            # Get all pending requests (filtered by user if specified)
            if user:
                cursor.execute("""
                    SELECT request_number, user_id, amount, player, attribute
                    FROM attribute_requests
                    WHERE status = 'pending' AND server_id = ? AND user_id = ?
                    ORDER BY request_number
                """, (server_id, user.id))
            else:
                cursor.execute("""
                    SELECT request_number, user_id, amount, player, attribute
                    FROM attribute_requests
                    WHERE status = 'pending' AND server_id = ?
                    ORDER BY request_number
                """, (server_id,))
            
            pending_requests = cursor.fetchall()
            
            if not pending_requests:
                if user:
                    await interaction.response.send_message(f"📭 No pending requests from {user.mention} to deny.", ephemeral=True)
                else:
                    await interaction.response.send_message("📭 No pending requests to deny.", ephemeral=True)
                return
            
            # Deny all requests
            denied_count = 0
            for req_id, user_id, player, attribute, amount in pending_requests:
                cursor.execute("UPDATE attribute_requests SET status = 'denied', updated_at = datetime('now', 'localtime') WHERE request_number = ?", (req_id,))
                
                # Log the denied request with reason to attributes_log
                cursor.execute("""
                    INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """, (user_id, server_id, 0, f"Request #{req_id} denied: {reason}", interaction.user.id))
                
                denied_count += 1
            
            conn.commit()
        
        # Build detailed response message
        if user:
            response_lines = [f"❌ **Denied {denied_count} requests from {user.mention}** successfully!"]
        else:
            response_lines = [f"❌ **Denied {denied_count} requests** successfully!"]
        
        for req_id, user_id, player, attribute, amount in pending_requests:
            response_lines.append(f"- Request #{req_id} by <@{user_id}> to upgrade {attribute} on {player} for {amount}pt(s) has been denied.")
        
        await interaction.response.send_message(
            "\n".join(response_lines),
            ephemeral=False
        )
        
        # Send DM notifications to all denied users
        for req_id, user_id, player, attribute, amount in pending_requests:
            try:
                user = interaction.guild.get_member(user_id)
                if user:
                    dm_embed = discord.Embed(
                        title="❌ Attribute Request Denied",
                        description=f"Your request to upgrade **{attribute}** on **{player}** has been denied.",
                        color=discord.Color.red()
                    )
                    dm_embed.add_field(name="Request #", value=f"#{req_id}", inline=True)
                    dm_embed.add_field(name="Points Requested", value=f"{amount}pt(s)", inline=True)
                    dm_embed.add_field(name="Denied By", value=interaction.user.display_name, inline=True)
                    dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                    dm_embed.add_field(name="", value="", inline=False)  # Spacing
                    dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                    dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                    
                    await user.send(embed=dm_embed)
                    print(f"[deny_all_requests] DM sent to user {user_id} for denied request #{req_id}")
            except Exception as e:
                print(f"[deny_all_requests] Failed to send DM to user {user_id}: {e}")

        await log_points_action(
            interaction,
            "❌ All Attribute Requests Denied",
            f"**Denied:** {denied_count} requests\n**By:** {interaction.user.mention}\n**Reason:** {reason}",
            discord.Color.red()
        )

    @attributes_group.command(name="deny", description="Deny a pending upgrade request.")
    @app_commands.describe(
        request_number="Select a pending request to deny",
        reason="(Optional) Reason for denying this request."
    )
    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @log_command("attributes deny")
    async def deny_request(interaction: Interaction, request_number: int, reason: str = "No reason provided"):
        await handle_request_action(interaction, request_number, decision="deny", reason=reason)

    @approve_request.autocomplete("request_number")
    @deny_request.autocomplete("request_number")
    async def autocomplete_pending_requests(interaction: discord.Interaction, current: str):
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT request_number, user_id, player, attribute, amount
                FROM attribute_requests
                WHERE status = 'pending' AND server_id = ?
                ORDER BY timestamp DESC
                LIMIT 25
            """, (server_id,))
            rows = cursor.fetchall()

        results = []
        for req_id, user_id, player, attribute, amount in rows:
            user = interaction.guild.get_member(user_id)
            display = user.display_name if user else f"User {user_id}"
            label = f"#{req_id} | {attribute} → {player} ({amount}pt) by {display}"
            if current in str(req_id):
                results.append(app_commands.Choice(name=label, value=req_id))

        return results[:25]


    async def handle_request_action(interaction: Interaction, request_number: int, decision: str, reason: str = "No reason provided"):
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, amount, player, attribute, status
                FROM attribute_requests
                WHERE request_number = ? AND server_id = ?
            """, (request_number, server_id))
            request = cursor.fetchone()

            if not request:
                await interaction.response.send_message("❌ No matching request found.", ephemeral=True)
                return

            user_id, amount, player, attribute, current_status = request

            if current_status != "pending":
                await interaction.response.send_message("⚠️ This request has already been processed.", ephemeral=True)
                return

            if decision == "deny":
                cursor.execute("UPDATE attribute_requests SET status = 'denied', updated_at = datetime('now', 'localtime') WHERE request_number = ?", (request_number,))
                
                # Log the denied request with reason to attributes_log
                cursor.execute("""
                    INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """, (user_id, server_id, 0, f"Request #{request_number} denied: {reason}", interaction.user.id))
                
                conn.commit()

                await interaction.response.send_message(
                    f"❌ Request #{request_number} by <@{user_id}> to upgrade `{attribute}` on **{player}** has been **denied**.\n📌 **Reason:** {reason}",
                    ephemeral=False
                )

                # Send DM notification to the user
                try:
                    user = interaction.guild.get_member(user_id)
                    if user:
                        dm_embed = discord.Embed(
                            title="❌ Attribute Request Denied",
                            description=f"Your request to upgrade **{attribute}** on **{player}** has been denied.",
                            color=discord.Color.red()
                        )
                        dm_embed.add_field(name="Request #", value=f"#{request_number}", inline=True)
                        dm_embed.add_field(name="Points Requested", value=f"{amount}pt(s)", inline=True)
                        dm_embed.add_field(name="Denied By", value=interaction.user.display_name, inline=True)
                        dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                        dm_embed.add_field(name="Reason", value=reason, inline=False)
                        dm_embed.add_field(name="", value="", inline=False)  # Spacing
                        dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                        dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                        
                        await user.send(embed=dm_embed)
                        print(f"[deny_request] DM sent to user {user_id} for denied request #{request_number}")
                except Exception as e:
                    print(f"[deny_request] Failed to send DM to user {user_id}: {e}")

                await log_points_action(
                    interaction,
                    "❌ Attribute Request Denied",
                    f"**User:** <@{user_id}>\n**Player:** {player}\n**Attribute:** `{attribute}`\n**Amount:** {amount}pt(s)\n**Request #:** {request_number}\n**Reason:** {reason}",
                    discord.Color.red()
                )
                return

            # Approve path
            cursor.execute("SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?", (user_id, server_id))
            available_row = cursor.fetchone()
            available_points = available_row[0] if available_row else 0

            if available_points < amount:
                await interaction.response.send_message(
                    f"⚠️ Cannot approve — <@{user_id}> only has {available_points} available points (requested {amount}).",
                    ephemeral=True
                )
                return

            new_available = available_points - amount
            cursor.execute("UPDATE attribute_points SET available = ? WHERE user_id = ? AND server_id = ?", (new_available, user_id, server_id))
            cursor.execute("UPDATE attribute_requests SET status = 'approved', updated_at = datetime('now', 'localtime') WHERE request_number = ?", (request_number,))
            conn.commit()

        await interaction.response.send_message(
            f"✅ Request #{request_number} by <@{user_id}> to upgrade `{attribute}` on **{player}** for **{amount}pt(s)** has been **approved**.",
            ephemeral=False
        )

        # Send DM notification to the user
        try:
            user = interaction.guild.get_member(user_id)
            if user:
                dm_embed = discord.Embed(
                    title="✅ Attribute Request Approved!",
                    description=f"Your request to upgrade **{attribute}** on **{player}** has been approved!",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Request #", value=f"#{request_number}", inline=True)
                dm_embed.add_field(name="Points Spent", value=f"{amount}pt(s)", inline=True)
                dm_embed.add_field(name="Approved By", value=interaction.user.display_name, inline=True)
                dm_embed.add_field(name="Total Remaining", value=f"{new_available}pt(s)", inline=True)
                dm_embed.add_field(name="League", value=interaction.guild.name, inline=True)
                dm_embed.add_field(name="", value="", inline=False)  # Spacing
                dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
                dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
                
                await user.send(embed=dm_embed)
                print(f"[approve_request] DM sent to user {user_id} for approved request #{request_number}")
        except Exception as e:
            print(f"[approve_request] Failed to send DM to user {user_id}: {e}")

        await log_points_action(
            interaction,
            "✅ Attribute Request Approved",
            f"**User:** <@{user_id}>\n**Player:** {player}\n**Attribute:** `{attribute}`\n**Amount:** {amount}pt(s)\n**Request #:** {request_number}",
            discord.Color.green()
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="pending", description="View all pending attribute upgrade requests.")
    @log_command("attributes pending")
    async def list_requests(interaction: discord.Interaction):
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT request_number, user_id, player, attribute, amount
                FROM attribute_requests
                WHERE status = 'pending' AND server_id = ?
                ORDER BY timestamp ASC
            """, (server_id,))
            requests = cursor.fetchall()

        if not requests:
            await interaction.response.send_message("✅ There are no pending attribute requests at the moment.", ephemeral=True)
            return

        response = ["**Pending Attribute Upgrade Requests:**"]
        for req_id, user_id, player, attribute, amount in requests:
            response.append(f"⏳ `#{req_id}` <@{user_id}> wants to upgrade **{attribute}** on **{player}** for **{amount}pt(s)**")

        await interaction.response.send_message("\n".join(response), ephemeral=True)

    @subscription_required(allowed_skus=PRO_SKUS)
    @attributes_group.command(name="history", description="View your own point request history (or others if you're a commissioner).")
    @app_commands.describe(user="Whose history you want to view. Leave blank to view your own.")
    @log_command("attributes history")
    async def points_history(interaction: discord.Interaction, user: discord.Member = None):
        viewer = interaction.user
        target = user or viewer
        server_id = str(interaction.guild.id)

        # Restrict access if not commissioner
        if target.id != viewer.id and not any(role.name in {"Commish", "Commissioners", "Commissioner"} for role in viewer.roles):
            await interaction.response.send_message("🚫 You can only view your own request history.", ephemeral=True)
            return

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT request_number, player, attribute, amount, status
                FROM attribute_requests
                WHERE user_id = ? AND server_id = ?
                ORDER BY request_number DESC
                LIMIT 10
            """, (target.id, server_id))
            records = cursor.fetchall()

        if not records:
            msg = "📭 You have no upgrade request history yet." if target.id == viewer.id else f"📭 <@{target.id}> has no request history."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        status_emojis = {
            "approved": "✅",
            "denied": "❌",
            "pending": "⏳"
        }

        response = [f"📚 **Attribute Request History for <@{target.id}>:**"]
        for req_id, player, attr, amt, status in records:
            emoji = status_emojis.get(status.lower(), "")
            response.append(f"• `#{req_id}` `{attr}` → **{player}** for **{amt}pt(s)** — {emoji} `{status.capitalize()}`")

        await interaction.response.send_message("\n".join(response), ephemeral=True)

    @subscription_required(allowed_skus=PRO_SKUS)
    @attributes_group.command(name="cancel-request", description="Cancel one of your pending attribute upgrade requests.")
    @app_commands.describe(
        request_number="The # of the request you want to cancel."
    )
    @log_command("attributes cancel-request")
    async def cancel_request(interaction: discord.Interaction, request_number: int):
        user_id = interaction.user.id
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status, user_id FROM attribute_requests
                WHERE request_number = ? AND server_id = ?
            """, (request_number, server_id))
            request = cursor.fetchone()

            if not request:
                await interaction.response.send_message("❌ No matching request found.", ephemeral=True)
                return

            status, request_user_id = request

            if request_user_id != user_id:
                await interaction.response.send_message("🚫 You can only cancel your own requests.", ephemeral=True)
                return

            if status != "pending":
                await interaction.response.send_message("⚠️ Only pending requests can be canceled.", ephemeral=True)
                return

            cursor.execute("""
                DELETE FROM attribute_requests
                WHERE request_number = ? AND user_id = ? AND server_id = ?
            """, (request_number, user_id, server_id))
            conn.commit()

        await interaction.response.send_message(f"🗑️ Request `#{request_number}` has been canceled successfully.", ephemeral=False)
        
        await log_points_action(
            interaction,
            "🗑️ Attribute Request Canceled",
            f"**User:** {interaction.user.mention}\n**Request #:** {request_number}",
            discord.Color.orange()
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="revoke", description="Manually revoke attribute points from a user.")
    @app_commands.describe(
        user="The user to revoke points from.",
        amount="Amount of points to revoke.",
        reason="(Optional) Reason for revoking these points."
    )
    @log_command("attributes revoke")
    async def revoke_points(
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        reason: str = "No reason provided"
    ):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user.id, server_id)
            )
            row = cursor.fetchone()

            if not row:
                await interaction.response.send_message(f"{user.mention} does not have any points on record.", ephemeral=True)
                return

            available = row[0]
            if available < amount:
                await interaction.response.send_message(
                    f"{user.mention} only has **{available}** points available. Cannot revoke {amount}.",
                    ephemeral=True
                )
                return

            new_available = available - amount
            cursor.execute(
                "UPDATE attribute_points SET available = ? WHERE user_id = ? AND server_id = ?",
                (new_available, user.id, server_id)
            )

            cursor.execute("""
                INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (user.id, server_id, -amount, reason, interaction.user.id))

            conn.commit()

        await interaction.response.send_message(
            f"🚫 Revoked **{amount} points** from {user.mention}\n📌 **Reason:** {reason}",
            ephemeral=False
        )

        # Send DM notification to the user
        try:
            dm_embed = discord.Embed(
                title="🚫 Attribute Points Revoked",
                description=f"**{amount} attribute point{'s' if amount != 1 else ''}** have been revoked from your account.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Total Remaining", value=f"{new_available}pt(s)", inline=True)
            dm_embed.add_field(name="Revoked By", value=interaction.user.display_name, inline=True)
            dm_embed.add_field(name="Server", value=interaction.guild.name, inline=True)
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="", value="", inline=False)  # Spacing
            dm_embed.add_field(name="—", value="*Do not reply to this DM. Send all attribute commands to Trilo in your league.*", inline=False)
            dm_embed.set_footer(text="Trilo • The Dynasty League Assistant")
            
            await user.send(embed=dm_embed)
            print(f"[revoke_points] DM sent to user {user.id} for {amount} points revoked")
        except Exception as e:
            print(f"[revoke_points] Failed to send DM to user {user.id}: {e}")

        await log_points_action(
            interaction,
            "➖ Attribute Points Revoked",
            f"**From:** {user.mention}\n**Amount:** {amount}\n**Reason:** {reason}",
            discord.Color.red()
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="check-user", description="Check how many attribute points a user has.")
    @app_commands.describe(user="The user whose points you want to check.")
    @log_command("attributes check-user")
    async def check_user_points(interaction: discord.Interaction, user: discord.Member):
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user.id, server_id)
            )
            row = cursor.fetchone()

        available = row[0] if row else 0

        await interaction.response.send_message(
            f"🔍 **{user.display_name}** currently has **{available} attribute point{'s' if available != 1 else ''}** available.",
            ephemeral=True
        )

    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="check-all", description="Check all users and their available attribute points.")
    @log_command("attributes check-all")
    async def view_all_points(interaction: discord.Interaction):
        server_id = str(interaction.guild.id)

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
            await interaction.response.send_message("📭 No users have points recorded yet.", ephemeral=True)
            return

        lines = ["📋 **All Users' Available Attribute Points:**"]
        for user_id, available in records:
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"<@{user_id}>"
            lines.append(f"• {name}: **{available}pt{'s' if available != 1 else ''}**")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
        
        
    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="clear-all", description="Clear all attribute points from all users in the server.")
    @log_command("attributes clear-all")
    async def clear_all_points(interaction: discord.Interaction):
        server_id = str(interaction.guild.id)

        view = ConfirmClearAllPointsView(interaction, server_id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to **clear ALL attribute points** for every user in this server?",
            view=view,
            ephemeral=True
        )


    @subscription_required(allowed_skus=PRO_SKUS)
    @commissioner_only()
    @attributes_group.command(name="revoke-all-from-user", description="Reset a user's available attribute points to 0.")
    @app_commands.describe(
        user="The user whose points you want to reset.",
        reason="(Optional) Reason for revoking all their points."
    )
    @log_command("attributes revoke-all-from-user")
    async def revoke_all_from_user(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        server_id = str(interaction.guild.id)

        with get_db_connection("attributes") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT available FROM attribute_points WHERE user_id = ? AND server_id = ?",
                (user.id, server_id)
            )
            row = cursor.fetchone()

            if not row:
                await interaction.response.send_message(f"{user.mention} does not have any points on record.", ephemeral=True)
                return

            available = row[0]
            if available == 0:
                await interaction.response.send_message(f"{user.mention} already has 0 points.", ephemeral=True)
                return

            cursor.execute(
                "UPDATE attribute_points SET available = 0 WHERE user_id = ? AND server_id = ?",
                (user.id, server_id)
            )
            cursor.execute("""
                INSERT INTO attributes_log (user_id, server_id, amount, reason, given_by, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (user.id, server_id, -available, f"Full reset: {reason}", interaction.user.id))
            conn.commit()

        await interaction.response.send_message(
            f"🛑 **Reset {available} points** from {user.mention}\n📌 **Reason:** {reason}",
            ephemeral=False
        )

        await log_points_action(
            interaction,
            "🔻 Full Attribute Point Reset",
            f"**User:** {user.mention}\n**Amount Reset:** {available}\n**Reason:** {reason}",
            discord.Color.dark_red()
        )

    
    
    # Overview command removed - use /help feature attributes instead




    bot.tree.add_command(attributes_group)
