"""
Youtube Seasonal Playlist Cog for Red-DiscordBot
------------------------------------------------

Required deps (inside `/data/venv`):
    !pip install --upgrade google-auth-oauthlib google-api-python-client google-auth
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Dict, Optional

import discord
from redbot.core import checks, commands, Config

# YouTube API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("red.youtubeplaylist")
log.setLevel(logging.INFO)
log.propagate = True

YOUTUBE_LINK_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/)|youtu\.be/)(?P<id>[A-Za-z0-9_-]{11})",
    flags=re.IGNORECASE,
)

_SEASONS = {
    "Winter": (12, 1, 2),
    "Spring": (3, 4, 5),
    "Summer": (6, 7, 8),
    "Fall":   (9, 10, 11),
}


class YoutubePlaylistListener(commands.Cog):
    """Collect YouTube links and keep seasonal playlists up-to-date."""

    def __init__(self, bot):
        self.bot = bot
        self.scopes = [
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]

        self.config = Config.get_conf(self, identifier=4072712025, force_registration=True)
        self.config.register_guild(
            channel_id=None,
            playlists={},
            added_video_ids=[],
            contributors={},
        )

        self.yt_service: Optional[object] = None
        self.bot.loop.create_task(self._startup())

    # ------------------------------------------------------------------
    # Startup & credential handling
    # ------------------------------------------------------------------
    async def _startup(self):
        await self.bot.wait_until_ready()
        try:
            self.yt_service = await asyncio.to_thread(self._build_youtube_service)
            log.info("YouTube API client initialised.")
        except Exception:
            log.exception("Failed to create YouTube API client:")

    def _build_youtube_service(self):
        cred_path = "data/YoutubePlaylistCog/credentials.json"
        token_path = "data/YoutubePlaylistCog/token.json"

        creds: Credentials | None = None
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            except Exception as exc:
                log.warning("Ignoring corrupt token.json (%s) – starting new OAuth flow", exc)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(
                        f"credentials.json missing – copy Google OAuth client secrets to {cred_path}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(cred_path, self.scopes)
                if hasattr(flow, "run_console"):
                    log.info("Opening OAuth consent (console)… paste code →")
                    creds = flow.run_console()
                else:
                    log.info("Opening OAuth consent (copy-paste)… URL below →")
                    creds = flow.run_local_server(port=8080, open_browser=False)
            with open(token_path, "w", encoding="utf-8") as fp:
                fp.write(creds.to_json())
                log.info("Saved new refresh token to token.json")

        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def _season_year(dt: datetime) -> str:
        month = dt.month
        year = dt.year

        # If it’s January or February, attribute it to the *previous* December’s winter.
        if month in (1, 2):
            return f"Winter {year - 1} - What Are You Listening To?"

        # If it’s December, it belongs to "Winter <this calendar year>""
        if month == 12:
            return f"Winter {year} - What Are You Listening To?"

        # Otherwise, fall back to normal season/Year = current dt.year
        if month in (3, 4, 5):
            return f"Spring {year} - What Are You Listening To?"
        if month in (6, 7, 8):
            return f"Summer {year} - What Are You Listening To?"
        if month in (9, 10, 11):
            return f"Fall {year} - What Are You Listening To?"

        return f"Unknown {year}"

    # ------------------------------------------------------------------
    # Playlist utilities
    # ------------------------------------------------------------------
    async def _ensure_playlist(self, guild: discord.Guild, season_year: str) -> str:
        playlists: Dict[str, str] = await self.config.guild(guild).playlists()
        if season_year in playlists:
            return playlists[season_year]

        body = {
            "snippet": {
                "title": season_year,
                "description": f"Auto-generated playlist of links posted in {guild.name} during {season_year}.",
            },
            # Set new playlists to public by default
            "status": {"privacyStatus": "public"},
        }
        def create_playlist():
            return self.yt_service.playlists().insert(
                part="snippet,status", body=body
            ).execute()
        resp = await asyncio.to_thread(create_playlist)
        playlist_id = resp["id"]
        playlists[season_year] = playlist_id
        await self.config.guild(guild).playlists.set(playlists)
        log.info("Created playlist %s (%s) for guild %s", season_year, playlist_id, guild.id)
        return playlist_id

    async def _add_video(self, playlist_id: str, video_id: str) -> bool:
        """Insert a video into the playlist, skipping missing videos. Return True if added"""
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }
        def insert_item():
            return self.yt_service.playlistItems().insert(
                part="snippet", body=body
            ).execute()
        try:
            await asyncio.to_thread(insert_item)
            return True
        except HttpError as e:
            status = getattr(e.resp, 'status', None)
            # 409 = duplicate, 404 = video not found; both can be ignored
            if status in (409, 404):
                log.warning("Skipping video %s: %s", video_id, e.error_details if hasattr(e, 'error_details') else e)
                return False

    async def _process_message(self, message: discord.Message) -> bool:
        matches = YOUTUBE_LINK_REGEX.findall(message.content)
        if not matches or self.yt_service is None:
            return False

        conf = self.config.guild(message.guild)
        added = await conf.added_video_ids()
        contributors = await conf.contributors()
        wrote_any = False

        for vid in matches:
            if vid in added:
                continue
            playlist_id = await self._ensure_playlist(
                message.guild, self._season_year(message.created_at)
            )
            added_success = await self._add_video(playlist_id, vid)

            if not added_success:
                continue

            added.append(vid)
            wrote_any = True
            uid = str(message.author.id)
            contributors[uid] = contributors.get(uid, 0) + 1

        if wrote_any:
            await conf.added_video_ids.set(added)
            await conf.contributors.set(contributors)
        return wrote_any

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------
    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        channel_id = await self.config.guild(message.guild).channel_id()
        if channel_id is None or message.channel.id != channel_id:
            return
        try:
            if await self._process_message(message):
                await message.add_reaction("🤖")
        except Exception:
            log.exception(f"Failed processing message {message.id}")

    # ------------------------------------------------------------------
    # Commands – ytpl group
    # ------------------------------------------------------------------
    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def ytpl(self, ctx: commands.Context):
        """YouTube seasonal playlist configuration."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @ytpl.command(name="setchannel")
    async def _setchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"✅ Monitoring {channel.mention} for YouTube links.")

    @ytpl.command(name="scrapeall")
    async def _scrapeall(self, ctx: commands.Context):
        channel_id = await self.config.guild(ctx.guild).channel_id()
        if channel_id is None:
            return await ctx.send("⚠️ Monitoring channel not configured.")
        channel = ctx.guild.get_channel(channel_id)
        if channel is None:
            return await ctx.send("⚠️ Configured channel invalid; please re-set.")
        msg = await ctx.send(f"⏳ Back-filling {channel.mention} history…")
        count = 0
        async for m in channel.history(limit=None, oldest_first=True):
            if await self._process_message(m):
                await m.add_reaction("🤖")
                count += 1
        await msg.edit(content=f"✅ Finished. Added **{count}** videos.")

    @ytpl.command(name="resetmetadata")
    @checks.admin_or_permissions(manage_guild=True)
    async def _resetmetadata(self, ctx: commands.Context):
        """Reset all stored YouTube metadata for this server."""
        await self.config.guild(ctx.guild).playlists.set({})
        await self.config.guild(ctx.guild).added_video_ids.set([])
        await self.config.guild(ctx.guild).contributors.set({})
        await ctx.send("✅ All YouTube metadata cleared. Use `!ytpl scrapeall` or post new links to repopulate.")

    @ytpl.command(name="metadata")
    async def _metadata(self, ctx: commands.Context):
        """Show collected video/playlist stats."""
        added = await self.config.guild(ctx.guild).added_video_ids()
        playlists = await self.config.guild(ctx.guild).playlists()
        contributors = await self.config.guild(ctx.guild).contributors()
        total_links = len(added)
        total_playlists = len(playlists)
        sorted_contrib = sorted(contributors.items(), key=lambda kv: kv[1], reverse=True)
        lines = [
            f"**Total links:** {total_links}",
            f"**Total playlists:** {total_playlists}",
            "",
            "**Contributors:**"
        ]
        for uid, num in sorted_contrib:
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else uid
            pct = (num / total_links * 100) if total_links else 0
            lines.append(f"• **{name}** – {num} links ({pct:.1f}%)")
        embed = discord.Embed(title="YouTube Collector Stats", description="\n".join(lines))
        await ctx.send(embed=embed)