# utils/entitlements.py
import aiohttp
import os

ENV = (os.getenv("ENV") or "dev").lower()
TOKEN = os.getenv("DISCORD_TOKEN") if ENV == "prod" else os.getenv("DEV_DISCORD_TOKEN")

async def get_guild_entitlements(guild_id: str):
    url = f"https://discord.com/api/v10/applications/@me/guilds/{guild_id}/entitlements"
    headers = {
        "Authorization": f"Bot {TOKEN}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"[Entitlements] Failed to fetch: {resp.status}")
                return []
            return await resp.json()
