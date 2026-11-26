import asyncio
import logging
import os
import re
from datetime import time

import aiohttp
import discord
from discord.ext import tasks
from redbot.core import commands

from .PMPAdmin import LA_TZ, PMP_GUILD_ID


log = logging.getLogger(__name__)
PROJECT_URL_PATTERN = re.compile(r"https://[a-z0-9]+\.supabase\.co")
SECRET_KEY_PATTERN = re.compile(r"sb_secret_[A-Za-z0-9_-]+")


class MemberSyncError(Exception):
    """A sync failure safe to report in logs and Discord."""


class SupabaseMemberSync(commands.Cog):
    """Mirror the current PMP member roster to Supabase."""

    def __init__(self, bot):
        self.bot = bot
        self._sync_lock = asyncio.Lock()

    async def cog_load(self):
        self.nightly_sync.start()

    def cog_unload(self):
        self.nightly_sync.cancel()

    @tasks.loop(time=time(hour=0, tzinfo=LA_TZ))
    async def nightly_sync(self):
        # Both settings are optional until the deployment opts in.
        if not (os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_SECRET_KEY")):
            return
        try:
            count = await self._sync_members()
        except MemberSyncError as error:
            log.warning("Nightly Supabase member sync failed: %s", error)
        else:
            log.info("Synced %d PMP members to Supabase.", count)

    @nightly_sync.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()

    @commands.command(name="supabasesync")
    @commands.is_owner()
    async def sync_now(self, ctx):
        """Run the PMP member sync to Supabase now."""
        try:
            async with ctx.typing():
                count = await self._sync_members()
        except MemberSyncError as error:
            await ctx.send(f"Supabase member sync failed. {error}")
        else:
            await ctx.send(f"Synced {count} PMP members to Supabase.")

    async def _sync_members(self):
        async with self._sync_lock:
            project_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
            secret_key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
            if not project_url or not secret_key:
                raise MemberSyncError("Set SUPABASE_URL and SUPABASE_SECRET_KEY on the bot host.")
            if not PROJECT_URL_PATTERN.fullmatch(project_url) or not SECRET_KEY_PATTERN.fullmatch(secret_key):
                raise MemberSyncError("Use the Supabase project URL and an sb_secret_ API key.")

            guild = self.bot.get_guild(PMP_GUILD_ID)
            if not self.bot.is_ready() or guild is None or guild.unavailable:
                raise MemberSyncError("The PMP server is unavailable.")
            if not self.bot.intents.members:
                raise MemberSyncError("Enable the Discord Server Members Intent for the bot.")

            members = []
            try:
                async for member in guild.fetch_members(limit=None):
                    members.append({
                        "user_id": str(member.id),
                        "roles": [
                            {"id": str(role.id), "name": role.name}
                            for role in member.roles
                            if not role.is_default()
                        ],
                    })
            except discord.HTTPException as error:
                raise MemberSyncError(f"Discord could not list members (HTTP {error.status}).") from None

            if not members:
                raise MemberSyncError("Discord returned an empty member list. The previous snapshot was kept.")

            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                    async with session.post(
                        f"{project_url}/rest/v1/rpc/sync_pmp_discord_members",
                        headers={"apikey": secret_key},
                        json={"p_guild_id": str(guild.id), "p_members": members},
                        allow_redirects=False,
                    ) as response:
                        if not 200 <= response.status < 300:
                            raise MemberSyncError(f"Supabase rejected the snapshot (HTTP {response.status}).")
            except (aiohttp.ClientError, TimeoutError):
                raise MemberSyncError("Could not complete the request to Supabase.") from None

            return len(members)
