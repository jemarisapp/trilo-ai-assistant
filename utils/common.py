# File: utils/common.py

from discord import app_commands
from utils.entitlements import get_guild_entitlements
from utils import get_db_connection
from datetime import datetime

DEFAULT_COMMISSIONER_ROLES = {"Commish", "Commissioners", "Commissioner"}

# ───────────────────────────────────────────────
# SKU Constants (Discord Premium App Subscriptions)
# ───────────────────────────────────────────────

SKU_ID_CORE_MONTHLY = "1386965677193302016"
SKU_ID_CORE_ANNUAL  = "1386985101631422474"
SKU_ID_PRO_MONTHLY  = "1386969404805353503"
SKU_ID_PRO_ANNUAL   = "1386985225560653844"

# ─ Plan Tiers ─
CORE_SKUS = {SKU_ID_CORE_MONTHLY, SKU_ID_CORE_ANNUAL}
PRO_SKUS  = {SKU_ID_PRO_MONTHLY, SKU_ID_PRO_ANNUAL}
ALL_PREMIUM_SKUS = CORE_SKUS | PRO_SKUS


# ───────────────────────────────────────────────
# Subscription Check
# ───────────────────────────────────────────────

def subscription_required(allowed_skus: set = ALL_PREMIUM_SKUS):
    async def predicate(interaction):
        guild_id = str(interaction.guild.id)

        # ✅ Bypass for development/test servers
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
            return True

        # ✅ Check Discord entitlements
        entitlements = await get_guild_entitlements(guild_id)
        active_skus = {e["sku_id"] for e in entitlements if e.get("ends_at") is None}

        if active_skus & allowed_skus:
            return True

        # ✅ Fallback: check internal DB for OTP/trial subscriptions
        try:
            with get_db_connection("keys") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT subscription_status, subscription_end_date
                    FROM server_subscriptions
                    WHERE guild_id = ? AND subscription_status = 'active'
                """, (guild_id,))
                row = cursor.fetchone()
                if row:
                    end_date = datetime.fromisoformat(row[1])
                    if datetime.utcnow() < end_date:
                        return True
                    else:
                        # 💥 Mark it as inactive in DB
                        cursor.execute("""
                            UPDATE server_subscriptions
                            SET subscription_status = 'inactive', updated_at = datetime('now', 'localtime')
                            WHERE guild_id = ?
                        """, (guild_id,))
                        conn.commit()

        except Exception as e:
            print(f"[Entitlement DB Fallback] {e}")

        await interaction.response.send_message(
            "🔒 This command requires a subscription. Subscribe in the bot’s profile or activate a trial.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


# ───────────────────────────────────────────────
# Role Checks
# ───────────────────────────────────────────────

def commissioner_only():
    async def predicate(interaction):
        from commands.settings import get_commissioner_roles  # avoid circular import
        server_id = str(interaction.guild.id)
        allowed_roles = get_commissioner_roles(server_id)

        user_roles = {role.name for role in interaction.user.roles}
        if allowed_roles & user_roles or interaction.user.guild_permissions.administrator:
            return True

        await interaction.response.send_message(
            "🚫 You must have one of the configured Commissioner roles to use this command.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


def admin_only():
    async def predicate(interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            "You need to be a server administrator to use this command.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)
