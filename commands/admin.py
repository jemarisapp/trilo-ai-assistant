# File: commands/admin.py
import os
import discord
from discord import app_commands
from discord import Embed
from discord.ext import commands
from utils.utils import get_db_connection, clean_team_key, format_team_name
from utils.common import commissioner_only, admin_only
from utils.command_logger import log_command
from datetime import datetime, timedelta
import asyncio

DEFAULT_COMMISSIONER_ROLES = {"Commish", "Commissioners", "Commissioner"}
""

def setup_admin_commands(bot: commands.Bot):
    admin_group = app_commands.Group(name="admin", description="Server registration tools")
    
    @admin_only()
    @admin_group.command(name="purchase", description="View Trilo's premium plans and unlock features.")
    @log_command("admin purchase")
    async def purchase_link(interaction: discord.Interaction):
        embed = Embed(
            title="🛒 Trilo Premium Plans",
            description=(
                "Upgrade your server to unlock Core and Pro features!\n\n"
                                 "🔹 **Core Tier**: Team Management, Messaging, Matchups, Win/Loss Records\n"
                 "🔸 **Pro Tier**: Attribute Points\n\n"
                "✨ You can choose monthly or annual plans via the Store."
            ),
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Open the Store",
            value="[Click here to view Trilo's Premium Store](https://discord.com/application-directory/1312633145216077854/store)",
            inline=False
        )
        embed.set_footer(text="Trilo • The Dynasty League Assistant")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @admin_only()
    @admin_group.command(name="trial", description="Start a 10-day trial for this server.")
    @log_command("admin trial")
    async def activate_trial(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        try:
            with get_db_connection("keys") as conn:
                cursor = conn.cursor()

                # Check if a trial has EVER been used
                cursor.execute("""
                    SELECT trial_used FROM server_subscriptions WHERE guild_id = ?
                """, (guild_id,))
                row = cursor.fetchone()

                if row and row[0]:  # trial_used is True
                    await interaction.response.send_message(
                        "🚫 This server has already used its free trial.",
                        ephemeral=True
                    )
                    return

                end_date = datetime.utcnow() + timedelta(days=10)

                # Activate trial and set trial_used = TRUE
                cursor.execute("""
                    INSERT INTO server_subscriptions (guild_id, plan_type, subscription_status, subscription_end_date, trial_used, created_at, updated_at)
                    VALUES (?, 'trial', 'active', ?, TRUE, datetime('now', 'localtime'), datetime('now', 'localtime'))
                    ON CONFLICT(guild_id) DO UPDATE SET
                        plan_type = 'trial',
                        subscription_status = 'active',
                        subscription_end_date = excluded.subscription_end_date,
                        trial_used = TRUE,
                        updated_at = datetime('now', 'localtime')
                """, (guild_id, end_date))

                conn.commit()

            await interaction.response.send_message(
                "🎉 Trial activated! You now have premium access for 10 Days.",
                ephemeral=True
            )

        except Exception as e:
            print(f"[Trial Activation Error] {e}")
            await interaction.response.send_message("❌ Failed to activate trial.", ephemeral=True)


    @admin_only()
    @admin_group.command(name="activate-annual", description="Activate your 1-year subscription after purchase.")
    @log_command("admin activate-annual")
    async def sync_otp_subscriptions(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        from utils.entitlements import get_guild_entitlements

        OTP_SKUS = {
            "1386985101631422474": "core",  # Core Annual
            "1386985225560653844": "pro",   # Pro Annual
        }

        entitlements = await get_guild_entitlements(guild_id)
        found_sku = next((e["sku_id"] for e in entitlements if e["sku_id"] in OTP_SKUS and e.get("ends_at") is None), None)

        if not found_sku:
            await interaction.response.send_message("❌ No valid annual subscription found for this server.", ephemeral=True)
            return

        plan = OTP_SKUS[found_sku]
        end_date = datetime.utcnow() + timedelta(days=365)

        try:
            with get_db_connection("keys") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO server_subscriptions (guild_id, plan_type, subscription_status, subscription_end_date, created_at, updated_at)
                    VALUES (?, ?, 'active', ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                    ON CONFLICT(guild_id) DO UPDATE SET
                        plan_type = excluded.plan_type,
                        subscription_status = 'active',
                        subscription_end_date = excluded.subscription_end_date,
                        updated_at = datetime('now', 'localtime')
                """, (guild_id, plan, end_date))
                conn.commit()

            await interaction.response.send_message(f"✅ `{plan.title()}` annual subscription activated until `{end_date.date()}`.", ephemeral=True)

        except Exception as e:
            print(f"[Sync OTP Error] {e}")
            await interaction.response.send_message("❌ Failed to sync subscription.", ephemeral=True)


    @admin_only()
    @admin_group.command(name="setup-league", description="Create a league-ready structure with channels and permissions.")
    @app_commands.describe(remove_existing_channels="Choose whether to delete all existing categories and channels.")
    @log_command("admin setup-league")
    async def setup_league(interaction: discord.Interaction, remove_existing_channels: bool = False):
        class ConfirmSetupView(discord.ui.View):
            def __init__(self, user, remove_existing):
                super().__init__(timeout=30)
                self.user = user
                self.remove_existing = remove_existing

            @discord.ui.button(label="✅ Confirm Setup", style=discord.ButtonStyle.success)
            async def confirm(self, i: discord.Interaction, button: discord.ui.Button):
                if i.user != self.user:
                    await i.response.send_message("You're not authorized to confirm this action.", ephemeral=True)
                    return
                await i.response.defer(ephemeral=True)
                await run_league_setup(i, self.remove_existing)
                self.stop()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, button: discord.ui.Button):
                if i.user != self.user:
                    await i.response.send_message("You're not authorized to cancel this.", ephemeral=True)
                    return
                await i.response.send_message("Setup canceled.", ephemeral=True)
                self.stop()

        await interaction.response.send_message(
            f"⚠️ This will set up a fresh league structure.{f' It will also delete all existing channels.' if remove_existing_channels else ''}\nDo you want to continue?",
            view=ConfirmSetupView(interaction.user, remove_existing_channels),
            ephemeral=True
        )

    async def run_league_setup(interaction: discord.Interaction, remove_existing: bool):
        guild = interaction.guild
        total_created = 0

        if remove_existing:
            for cat in guild.categories:
                for ch in cat.channels:
                    await ch.delete()
                await cat.delete()
            for ch in guild.text_channels:
                await ch.delete()

        server_id = str(guild.id)
        allowed_roles = DEFAULT_COMMISSIONER_ROLES.copy()
        try:
            with get_db_connection("keys") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT new_value FROM server_settings
                    WHERE server_id = ? AND setting = 'commissioner_roles'
                """, (server_id,))
                row = cursor.fetchone()
                if row:
                    allowed_roles = {r.strip() for r in row[0].split(",")}
        except Exception as e:
            print(f"[setup-league] Failed to load commissioner roles: {e}")

        commish_roles = [role for role in guild.roles if role.name in allowed_roles]

        structure = {
            "Commish": [("commish-chat", "commish_only"), ("trilo-commands", "commish_only")],
            "Main Channels": [("main-chat", "public"), ("live-streams", "public"), ("announcements", "public_read_commish_write")],
            "League Info": [("league-info", "public_read_commish_write"), ("league-rules", "public_read_commish_write"), ("team-assignments", "public_read_commish_write"), ("team-conferences", "public_read_commish_write")],
            "Matchups": [("team-1-vs-team-2", "public"), ("team-3-vs-team-4", "public")]
        }

        async def create_with_permissions(category, name, access_level):
            overwrites = {guild.default_role: discord.PermissionOverwrite()}
            if access_level == "commish_only":
                overwrites[guild.default_role].read_messages = False
                for r in commish_roles:
                    overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            elif access_level == "public_read_commish_write":
                overwrites[guild.default_role].read_messages = True
                overwrites[guild.default_role].send_messages = False
                for r in commish_roles:
                    overwrites[r] = discord.PermissionOverwrite(send_messages=True)
            else:
                overwrites[guild.default_role].read_messages = True
                overwrites[guild.default_role].send_messages = True

            return await guild.create_text_channel(name, overwrites=overwrites, category=category)

        
        created_channels = []

        for cat_name, ch_list in structure.items():
            category = await guild.create_category(cat_name)
            for ch_name, level in ch_list:
                channel = await create_with_permissions(category, ch_name, level)
                created_channels.append(channel.mention)

                if ch_name == "main-chat":
                    try:
                        await guild.edit(system_channel=channel)
                        print("[Trilo] System channel set to #main-chat")
                    except Exception as e:
                        print(f"[Trilo] Failed to set system channel: {e}")

                                     
        # Send embed summary to commish-chat
        await asyncio.sleep(1)  # Short delay to ensure channels are synced
        commish_channel = next((c for c in guild.text_channels if c.name == "commish-chat"), None)
        if commish_channel:
            embed = discord.Embed(
                title="🏗️ League Setup Complete",
                description=f"Trilo has created {len(created_channels)} channels across multiple categories.",
                color=discord.Color.green()
            )
            embed.add_field(name="Categories Created", value="\n".join(structure.keys()), inline=False)
            embed.add_field(name="Removed Old Channels", value="✅ Yes" if remove_existing else "❌ No", inline=False)
            embed.set_footer(text="Trilo • The Dynasty League Assistant")
            await commish_channel.send(embed=embed)
        
        print(f"[Trilo] League setup completed in {guild.name} ({guild.id}) with {len(created_channels)} channels.")

    
    
    @admin_group.command(name="guide", description="View a comprehensive setup walkthrough to help you get started.")
    @log_command("admin guide")
    async def admin_guide(interaction: discord.Interaction):
        # Create multiple embeds for better organization
        embeds = []
        
        # Main setup guide embed
        embed1 = discord.Embed(
            title="🛠️ Trilo Setup Guide",
            description=(
                "💡 *To use a command, type `/` and begin typing its name.*\n"
                "🎮 *Or tap the Discord Controller icon (next to your keyboard) to browse available options and use the built-in forms.*\n\n"
                "**Complete Setup Walkthrough for New Trilo Servers**\n\n"
                "This guide will walk you through every step to get your dynasty league running smoothly with Trilo."
            ),
            color=discord.Color.blue()
        )
        embeds.append(embed1)
        
        # Step 1: Activation
        embed2 = discord.Embed(
            title="🔑 Step 1: Activate Trilo",
            description=(
                "**Choose Your Access Method:**\n\n"
                "**🎯 Free Trial:** Start with `/admin trial` for 10 days of full access\n"
                "**📋 View Plans:** See all options with `/admin purchase`\n"
                "**💎 Monthly Subscriptions:** Purchase from the Store - access is automatic\n"
                "**📅 Annual Subscriptions:** Purchase and activate with `/admin activate-annual`\n\n"
                "**After Activation:**\n"
                "• Use `/admin check-subscription` to confirm setup\n"
                "• Your server will be linked to Trilo\n"
                "• All premium features will be unlocked"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed2)
        
        # Step 2: Essential Settings
        embed3 = discord.Embed(
            title="⚙️ Step 2: Configure Essential Settings",
            description=(
                "**Must-Have Settings for League Operation:**\n\n"
                "**👑 Commissioner Roles:**\n"
                "• `/settings set commissioner_roles Commish,Admin,Owner`\n"
                "• **Choose your own role names** - separate multiple roles with commas\n"
                "• **Default roles** (if none set): Commish, Commissioners, Commissioner\n"
                "• These roles can use all commissioner commands\n\n"
                "**🔧 Available Settings:**\n"
                "• `commissioner_roles` — Set roles for commissioner commands\n"
                "• `record_tracking_enabled` — Enable/disable automatic record tracking\n"
                "• `attributes_log_channel` — Channel for attribute change logs\n"
                "• `stream_notify_role` — Role to ping for stream announcements\n"
                "• `stream_watch_channel` — Channel for stream notifications\n"
                "• `stream_announcements_enabled` — Enable/disable stream features\n\n"
                "**View Current Settings:** `/settings view`\n"
                "**Reset a Setting:** `/settings reset [setting_name]`"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed3)
        
        # Step 3: League Structure
        embed4 = discord.Embed(
            title="🏗️ Step 3: Create League Structure (Optional)",
            description=(
                "**Auto-Generate Your League Channels:**\n\n"
                "**Command:** `/admin setup-league`\n\n"
                "**What This Creates:**\n"
                "• **📋 Commish** — Private commissioner channels\n"
                "• **💬 Main Channels** — Public league discussion\n"
                "• **📚 League Info** — Rules, Team Assignments, Team Conferences\n"
                "• **🎮 Matchups** — Practice matchup channels\n\n"
                "**Customization:** You can modify or delete these categories later\n"
                "**Existing Channels:** Choose whether to remove old channels during setup"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed4)
        
        # Step 4: Team Management
        embed5 = discord.Embed(
            title="📝 Step 4: Assign Team Ownership",
            description=(
                "**Set Up Your League's Team Structure:**\n\n"
                "**Assign Teams:**\n"
                "• `/teams assign-user @user Team Name`\n"
                "• Example: `/teams assign-user @John Oregon`\n\n"
                "**Manage Assignments:**\n"
                "• `/teams list-all` — See all team assignments\n"
                "• `/teams who-has Oregon` — Check who owns a specific team\n"
                "• `/teams unassign-user @user` — Remove team ownership\n"
                "• `/teams clear-team Oregon` — Unassign a specific team\n\n"
                "**Bulk Operations:**\n"
                "• `/teams clear-all-assignments` — Reset all teams (use carefully!)"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed5)
        
        # Step 5: Matchup System
        embed6 = discord.Embed(
            title="📅 Step 5: Set Up Matchups",
            description=(
                "**Create and Manage Your League Schedule:**\n\n"
                "**Create Matchups:**\n"
                "• **📸 From Image:** `/matchups cfb-create-from-image` — Upload schedule screenshots\n"
                "• **✍️ Manual Entry:** `/matchups cfb-create-from-text` — Type matchups manually\n\n"
                "**Manage Matchups:**\n"
                "• `/matchups tag-users` — Auto-tag players in their game channels\n"
                "• `/matchups list-all` — View all current matchups\n"
                "• `/matchups sync-records` — Update with current team records\n\n"
                "**Game Tracking:**\n"
                "• Use reactions in matchup channels: ✅ Completed, 🎲 Fair Sim, ☑️ Force Win\n"
                "• Records automatically update when games are completed"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed6)
        
        # Step 6: Messaging Tools
        embed7 = discord.Embed(
            title="📣 Step 6: Messaging Tools",
            description=(
                "**Keep Your League Informed and Engaged:**\n\n"
                "**📢 Announcements:**\n"
                "• `/message custom` — Send custom messages to multiple channels\n"
                "• `/message announce-advance` — Notify of next advance time\n\n"
                "**💡 Best Practices:**\n"
                "• Use for weekly updates, rule changes, and important announcements\n"
                "• Send to multiple channels simultaneously for maximum visibility\n"
                "• Perfect for keeping everyone informed about league events"
            ),
            color=discord.Color.gold()
        )
        embeds.append(embed7)
        
        # Step 7: Advanced Features (Pro Only)
        embed8 = discord.Embed(
            title="🚀 Step 7: Advanced Features (Pro Only)",
            description=(
                "**Unlock Premium League Management Tools:**\n\n"
                "**📊 Attribute Points System:**\n"
                "• `/attributes give @user 100` — Award points to users\n"
                "• Users request upgrades with `/attributes request`\n"
                "• Manage requests with `/attributes approve-request`, `/attributes approve-all`, `/attributes deny-request`, or `/attributes deny-all`\n"
                "• View all requests with `/attributes requests-list`\n\n"
                "**🔍 Monitoring:**\n"
                "• `/attributes check-all` — View all user point balances\n"
                "• `/attributes requests-history` — Track upgrade history"
            ),
            color=discord.Color.purple()
        )
        embeds.append(embed8)
        
        # Step 8: Ongoing Management
        embed9 = discord.Embed(
            title="🔄 Step 8: Ongoing League Management",
            description=(
                "**Keep Your League Running Smoothly:**\n\n"
                "**Weekly Operations:**\n"
                "• Create new matchups with `/matchups create`\n"
                "• Tag users in games with `/matchups tag-users`\n"
                "• Delete old matchups with `/matchups delete`\n"
                "• Monitor game completion with matchup reactions\n\n"
                "**Troubleshooting:**\n"
                "• Check settings with `/settings view`\n"
                "• Verify registration with `/admin check-registration`\n"
                "• Use `/trilo help` for feature-specific guidance"
            ),
            color=discord.Color.green()
        )
        embeds.append(embed9)
        
        # Final help embed
        embed10 = discord.Embed(
            title="💬 Need More Help?",
            description=(
                "**📚 Comprehensive Help System:**\n"
                "• `/trilo help` — Get help with any Trilo feature\n"
                "• Select 'Getting Started & Overview' for a complete feature list\n"
                "• Filter help by audience (Everyone, Commissioners, League Members)\n\n"
                "**🔗 Support Resources:**\n"
                                 "• [Join our Support Server](https://t.co/YmCwbDvlV3)\n"
                "• Check `/admin purchase` for subscription options\n"
                "• Use `/admin trial` to test all features\n\n"
                "**💡 Pro Tips:**\n"
                "• Start with the free trial to explore all features\n"
                "• Use `/admin setup-league` for quick channel creation\n"
                "• Enable record tracking early for automatic standings"
            ),
            color=discord.Color.blue()
        )
        embed10.set_footer(text="Trilo • The Dynasty League Assistant")
        embeds.append(embed10)

        await interaction.response.send_message(embeds=embeds, ephemeral=False)

    @admin_group.command(name="check-subscription", description="Check your server's subscription status and plan details.")
    @log_command("admin check-subscription")
    async def check_subscription(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        # Check if server is whitelisted
        WHITELISTED_GUILDS = {
            "1375885708409180371",  # Test League
            "1316427693381914674",  # TRILO
            "1241080455306936472",  # LOB
            "1311498254940372992",  # DUH
            "1255041696949997610",  # BETA SERVER
            "1276298110380937400",  # @maink2019 - League 01
            "1324595304070381628",  # ZayBirk League
        }
        
        if guild_id in WHITELISTED_GUILDS:
            embed = discord.Embed(
                title="🔓 Subscription Status",
                description="**Status:** ✅ **WHITELISTED**\n**Access:** Full Premium Features\n**Plan:** Development/Testing Server",
                color=discord.Color.green()
            )
            embed.add_field(
                name="ℹ️ Note",
                value="This server has automatic access to all Trilo features for development and testing purposes.",
                inline=False
            )
            embed.set_footer(text="Trilo • The Dynasty League Assistant")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check Discord entitlements
        try:
            from utils.entitlements import get_guild_entitlements
            entitlements = await get_guild_entitlements(guild_id)
            
            # Check for active entitlements
            active_skus = []
            for entitlement in entitlements:
                if entitlement.get("ends_at") is None:  # Active subscription
                    sku_id = entitlement.get("sku_id")
                    if sku_id:
                        active_skus.append(sku_id)
            
            if active_skus:
                # Determine plan type from SKU
                plan_info = {}
                for sku in active_skus:
                    if sku == "1386965677193302016":  # Core Monthly
                        plan_info["Core Monthly"] = "Recurring monthly subscription"
                    elif sku == "1386985101631422474":  # Core Annual
                        plan_info["Core Annual"] = "One-time annual purchase"
                    elif sku == "1386969404805353503":  # Pro Monthly
                        plan_info["Pro Monthly"] = "Recurring monthly subscription"
                    elif sku == "1386985225560653844":  # Pro Annual
                        plan_info["Pro Annual"] = "One-time annual purchase"
                    else:
                        plan_info[f"Unknown Plan ({sku})"] = "Active subscription"
                
                # Show active subscription details
                embed = discord.Embed(
                    title="✅ Active Subscription",
                    description="Your server has an active premium subscription!",
                    color=discord.Color.green()
                )
                
                for plan_name, plan_desc in plan_info.items():
                    embed.add_field(
                        name=f"📋 Current Plan",
                        value=f"**{plan_name}**\n{plan_desc}",
                        inline=False
                    )
                
                embed.add_field(
                    name="🔄 Renewal",
                    value="**Automatic** - Discord handles renewal and access",
                    inline=False
                )
                
            else:
                # Check for trial or OTP subscriptions in database
                try:
                    with get_db_connection("keys") as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT plan_type, subscription_status, subscription_end_date
                            FROM server_subscriptions
                            WHERE guild_id = ? AND subscription_status = 'active'
                        """, (guild_id,))
                        row = cursor.fetchone()
                        
                        if row:
                            plan_type, status, end_date = row
                            end_date_obj = datetime.fromisoformat(end_date)
                            now = datetime.utcnow()
                            
                            if now < end_date_obj:
                                # Active trial or OTP
                                days_left = (end_date_obj - now).days
                                embed = discord.Embed(
                                    title="⏰ Active Trial/OTP",
                                    description=f"Your server has an active **{plan_type.title()}** subscription.",
                                    color=discord.Color.blue()
                                )
                                embed.add_field(
                                    name="📅 Expiration",
                                    value=f"**{end_date_obj.strftime('%B %d, %Y')}**\n**{days_left} days remaining**",
                                    inline=False
                                )
                                embed.add_field(
                                    name="📋 Plan Type",
                                    value=f"**{plan_type.title()}** - One-time purchase or trial",
                                    inline=False
                                )
                            else:
                                # Expired
                                embed = discord.Embed(
                                    title="❌ Subscription Expired",
                                    description="Your subscription has expired. Renew to continue using premium features.",
                                    color=discord.Color.red()
                                )
                                embed.add_field(
                                    name="📅 Expired On",
                                    value=f"**{end_date_obj.strftime('%B %d, %Y')}**",
                                    inline=False
                                )
                        else:
                            # No subscription found
                            embed = discord.Embed(
                                title="🔒 No Active Subscription",
                                description="Your server doesn't have an active subscription.",
                                color=discord.Color.red()
                            )
                            embed.add_field(
                                name="💡 Get Started",
                                value="• Use `/admin trial` for a 10-day free trial\n• Use `/admin purchase` to view premium plans",
                                inline=False
                            )
                            
                except Exception as e:
                    print(f"[Check Subscription DB Error] {e}")
                    embed = discord.Embed(
                        title="❌ Error Checking Subscription",
                        description="Unable to check subscription status. Please try again or contact support.",
                        color=discord.Color.red()
                    )
                    
        except Exception as e:
            print(f"[Check Subscription Entitlements Error] {e}")
            embed = discord.Embed(
                title="❌ Error Checking Subscription",
                description="Unable to check Discord entitlements. Please try again or contact support.",
                color=discord.Color.red()
            )
        
        embed.set_footer(text="Trilo • The Dynasty League Assistant")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(admin_group)
