from redbot.core import commands, Config, checks
import discord
import re
import asyncio
import io
from urllib.parse import urlparse
from collections import defaultdict
from typing import Dict, List, Tuple, DefaultDict, Optional

"""ChallengeScraper Cog
========================
Scrapes Discord **Forum Channels** that host daily challenge threads titled like
"DAY 1", "Day 2", etc. For each thread it extracts all **non‑image URLs** plus
**uploaded audio attachments**, grouping them by author, then aggregates the
results in a dedicated **Challenge Summary** thread inside the same forum.

Public behaviour
----------------
* Admin‑only `!scrapechallenge` updates/creates the per‑DAY summaries.
* If a summary > 2 000 chars, the cog **splits it across multiple messages** so
  everything remains readable in‑channel.

Debug behaviour
---------------
* `!scrapechallengedebug` runs the same scrape but posts privately (DM or test
  channel). When the preview exceeds 2 000 chars it falls back to an attached
  `.txt` file to avoid clutter.

Other highlights
----------------
* Filters out image/GIF links and **ignores Tenor & discord.com links** (except
  audio attachments hosted on Discord CDN).
* Summary lines ping users (`@User`) and comma‑separate URLs, each wrapped in
  `< >` to suppress embeds.
* Automatically updates when new DAY threads or messages appear.
* Handles Discord's length limits without raising errors.
"""

# ------------------------------------------------------------
# Constants & helpers
# ------------------------------------------------------------
DAY_PATTERN = re.compile(r"^day\s+\d+", re.I)
URL_PATTERN = re.compile(r"https?://\S+")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".gifv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
IGNORE_DOMAINS = {"tenor.com", "discord.com"}
DISCORD_LIMIT = 2000  # character limit per message


# ---------- Filtering helpers ----------

def _is_image_url(url: str) -> bool:
    return any(url.lower().endswith(ext) for ext in IMAGE_EXTS)

def _should_include(url: str) -> bool:
    """Return True if *url* should be included in the summary list."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.netloc.lower() in IGNORE_DOMAINS:
        return False
    if _is_image_url(url):
        return False
    return True

def _is_valid_url(url: str) -> bool:
        """Return True for URLs we keep (exclude images & ignored domains)."""
        if _is_image_url(url):
            return False
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host not in IGNORE_DOMAINS

def _is_audio_attachment(att: discord.Attachment) -> bool:
    if att.content_type and att.content_type.startswith("audio"):
        return True
    return any(att.filename.lower().endswith(ext) for ext in AUDIO_EXTS)

def _split_chunks(text: str, limit: int = DISCORD_LIMIT) -> List[str]:
    """
    Split *text* into ≤ *limit*-char chunks **while preserving line breaks**.

    The previous implementation concatenated lines without `\\n`, so summaries
    lost their line structure. This version keeps each line’s newline intact
    and only breaks on line boundaries.
    """
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    buffer: List[str] = []
    char_count = 0

    for line in text.splitlines(keepends=True):  # keep newline chars
        if char_count + len(line) > limit:
            chunks.append("".join(buffer))
            buffer = [line]
            char_count = len(line)
        else:
            buffer.append(line)
            char_count += len(line)

    if buffer:
        chunks.append("".join(buffer))

    return chunks

# ------------------------------------------------------------
# Main cog
# ------------------------------------------------------------
class ChallengeScraper(commands.Cog):
    """Scrapes "DAY n" forum threads and maintains Challenge Summary."""

    # -----------------------------------------------------
    # INIT / CONFIG
    # -----------------------------------------------------
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0xC0FFEE)
        self.config.register_guild(
            forum_channel_id=None,      # registered forum channel id
            summary_thread_id=None,     # id of the "Challenge Summary" thread
            thread_message_map={},      # {day_thread_id: summary_message_id}
        )
        self._locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # -----------------------------------------------------
    # Helper – forum / summary thread resolution
    # -----------------------------------------------------
    async def _get_forum(self, guild: discord.Guild) -> Optional[discord.ForumChannel]:
        fid = await self.config.guild(guild).forum_channel_id()
        chan = guild.get_channel(fid) if fid else None
        return chan if isinstance(chan, discord.ForumChannel) else None

    async def _ensure_summary_thread(self, forum: discord.ForumChannel) -> discord.Thread:
        """Ensure the *Challenge Summary* thread exists and return it."""
        cached = await self.config.guild(forum.guild).summary_thread_id()
        if cached:
            t = forum.get_thread(cached)
            if t:
                return t

        # Create summary thread – discord.py ≥2.4 returns (Thread, Message)
        created = await forum.create_thread(
            name="Challenge Summary",
            content="Initialising summary …",
        )
        thread = created[0] if isinstance(created, tuple) else created  # type: ignore
        # Lock so only bot can post
        try:
            await thread.edit(locked=True)
        except Exception:
            pass
        await self.config.guild(forum.guild).summary_thread_id.set(thread.id)
        return thread

    # ---------------- URL extraction helper ------------------
    def _extract_urls_from_message(self, msg: discord.Message) -> List[str]:
        """Return a list of valid links from message content plus any audio attachments."""
        urls = [u for u in URL_PATTERN.findall(msg.content) if _is_valid_url(u)]
        urls.extend(att.url for att in msg.attachments if _is_audio_attachment(att))
        return urls
    
    # -----------------------------------------------------
    # Helper – collect + format URLs & audio attachment links
    # -----------------------------------------------------
    # ---------------- Collection & formatting ------------------
    async def _collect_urls(self, thread: discord.Thread) -> list[tuple[str, list[str]]]:
        """
        Walk the thread and return a list of (author_display_name, [urls…]),
        alphabetised by name and with duplicate links removed.
        """
        per_user: DefaultDict[int, list[str]] = defaultdict(list)

        async for msg in thread.history(oldest_first=True, limit=None):
            links = self._extract_urls_from_message(msg)
            if links:
                per_user[msg.author.id].extend(links)

        records: list[tuple[str, list[str]]] = []
        for uid, urls in per_user.items():
            member = thread.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            deduped = sorted(dict.fromkeys(urls))  # preserve deterministic order
            records.append((name, deduped))

        records.sort(key=lambda t: t[0].lower())
        return records

    @staticmethod
    def _format(records: list[tuple[str, list[str]]], title: str) -> str:
        """
        Build the summary block.

        Example:
        Zach: [YouTube](<https://youtube.com/...>), [GitHub](<https://github.com/...>)
        """
        lines = [f"**{title}**"]
        for name, urls in records:
            links = []
            for u in urls:
                host = (urlparse(u).hostname or "").removeprefix("www.")
                # Angle-bracket the URL so Discord skips link previews
                links.append(f"[{host}](<{u}>)")
            lines.append(f"{name}: {', '.join(links)}")
        return "\n".join(lines)

    
    # -----------------------------------------------------
    # Helper – iterate all DAY threads (open + archived)
    # -----------------------------------------------------
    async def _iter_day_threads(self, forum: discord.ForumChannel) -> List[discord.Thread]:
        """Return list of DAY threads ordered oldest→newest."""
        threads = [t for t in forum.threads if DAY_PATTERN.match(t.name)]

        # Archived threads (discord.py ≥ 2.3)
        try:
            async for arch in forum.archived_threads(limit=None):
                if DAY_PATTERN.match(arch.name):
                    threads.append(arch)
        except AttributeError:
            pass  # method absent on older d.py

        threads.sort(key=lambda t: t.created_at or discord.utils.snowflake_time(t.id))
        return threads

    # -----------------------------------------------------
    # Messaging helpers
    # -----------------------------------------------------
    async def _send_content_or_file(self, destination: discord.abc.Messageable, content: str, filename: str) -> discord.Message:
        """Send *content* or fallback to file – used by DEBUG COMMAND ONLY."""
        if len(content) <= DISCORD_LIMIT:
            return await destination.send(content)
        fp = io.StringIO(content)
        file = discord.File(fp, filename=filename)
        return await destination.send("Summary too long – see attached file.", file=file)

    async def _split_and_send(
        self, thread: discord.Thread, content: str
    ) -> discord.Message:
        """
        Split *content* into ≤2 000-char chunks and send them sequentially.
        Returns the **first** message object (whose ID we track).
        """
        chunks = _split_chunks(content)
        first: Optional[discord.Message] = None
        for chunk in chunks:
            msg = await thread.send(chunk)
            first = first or msg
        return first

    async def _edit_or_split(
        self, existing: discord.Message, content: str
    ) -> discord.Message:
        """
        • If *content* ≤2 000, simply edit *existing*.
        • Otherwise delete *existing* **and** any immediately-following
          bot messages that belong to the same summary, then repost
          fresh chunks via _split_and_send.
        """
        if len(content) <= DISCORD_LIMIT:
            return await existing.edit(content=content)

        # ---- need to replace multi-part summary ----
        parent = existing.channel  # the summary thread
        after_id = existing.id
        await existing.delete()

        # Delete any subsequent bot messages that are part of the
        # same (now-stale) summary chunk chain.
        async for msg in parent.history(
            after=discord.Object(id=after_id),
            oldest_first=True,
            limit=20,          # sane upper-bound – tweak as needed
        ):
            if msg.author != self.bot.user:
                break  # somebody else spoke – stop cleaning
            # Heuristic: stop at the next **DAY n** header (another summary)
            if msg.content.startswith("**DAY"):
                break
            try:
                await msg.delete()
            except discord.HTTPException:
                pass

        # Re-send fresh chunks and return the first one
        return await self._split_and_send(parent, content)

    # -----------------------------------------------------
    # Helper – update/insert a summary message for a DAY thread
    # -----------------------------------------------------
    async def _update_summary_msg(self, summary_parent: discord.Thread, day_thread: discord.Thread):
        """Create/edit the summary message for *day_thread* inside *summary_parent*.
        The first chunk's message ID is tracked so future updates replace it."""
        async with self._locks[day_thread.id]:
            content = self._format(await self._collect_urls(day_thread), day_thread.name)

            # Retrieve saved mapping {day_thread_id: first_summary_msg_id}
            mapping = await self.config.guild(summary_parent.guild).thread_message_map()
            first_msg_id = mapping.get(str(day_thread.id))

            # Fetch existing summary message (if any)
            existing: Optional[discord.Message] = None
            if first_msg_id:
                try:
                    existing = await summary_parent.fetch_message(first_msg_id)
                except discord.NotFound:
                    existing = None

            # Edit or (re)send
            if existing:
                first = await self._edit_or_split(existing, content)
            else:
                first = await self._split_and_send(summary_parent, content)

            # Persist the new first‑message ID
            mapping[str(day_thread.id)] = first.id
            await self.config.guild(summary_parent.guild).thread_message_map.set(mapping)

    # -----------------------------------------------------
    # Commands
    # -----------------------------------------------------
    @commands.command(name="clearchallengesummary")
    @checks.admin_or_permissions(manage_guild=True)
    async def clear_challenge_summary(self, ctx: commands.Context):
        """
        Delete every bot-authored message in the “Challenge Summary” thread
        and reset the stored mapping, letting you start fresh.
        """
        forum = await self._get_forum(ctx.guild)
        if not forum:
            await ctx.send("Forum not registered. Use !registerchallengeforum.")
            return

        summary_thread = await self._ensure_summary_thread(forum)

        deleted = 0
        async for msg in summary_thread.history(limit=None, oldest_first=True):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                    deleted += 1
                except discord.HTTPException:
                    pass

        # Wipe the per-day → message-ID map so the next scrape repopulates cleanly
        await self.config.guild(ctx.guild).thread_message_map.set({})
        await ctx.send(f"🗑️  Cleared {deleted} summary message(s).")

    @commands.command(name="scrapechallenge")
    @checks.admin_or_permissions(manage_guild=True)
    async def scrape_challenge(self, ctx: commands.Context):
        """Manually rebuild the Challenge Summary for all DAY threads."""
        forum = await self._get_forum(ctx.guild)
        if not forum:
            await ctx.send("Forum not registered. Use !registerchallengeforum.")
            return

        summary_thread = await self._ensure_summary_thread(forum)
        day_threads = await self._iter_day_threads(forum)
        await ctx.send(f"Processing {len(day_threads)} threads…")
        for th in day_threads:
            await self._update_summary_msg(summary_thread, th)
        await ctx.send("✅ Challenge summary refreshed.")

    @commands.command(
        name="scrapechallengedebug",
        aliases=["scrapechallengepreview", "scrapechallengedemo"],
    )
    @checks.admin_or_permissions(manage_guild=True)
    async def scrape_challenge_debug(
        self,
        ctx: commands.Context,
        forum_id: Optional[int] = None,
        guild_id: Optional[int] = None,
    ):
        """Run scrape privately (DM/test channel). Optional forum_id & guild_id override."""
        guild = ctx.guild or (self.bot.get_guild(guild_id) if guild_id else None)
        if not guild:
            await ctx.send("Need guild_id when running from DM.")
            return

        forum = None
        if forum_id:
            ch = guild.get_channel(forum_id)
            if isinstance(ch, discord.ForumChannel):
                forum = ch
        else:
            forum = await self._get_forum(guild)

        if not forum:
            await ctx.send("Forum not found/registered.")
            return

        day_threads = await self._iter_day_threads(forum)
        sections: List[str] = []
        for th in day_threads:
            recs = await self._collect_urls(th)
            if recs:
                sections.append(self._format(recs, th.name))
        output = "\n\n".join(sections) or "(No links found.)"
        await self._send_content_or_file(ctx.channel, output, "challenge_debug.txt")

    # -----------------------------------------------------
    # Listeners – auto‑update on new threads / messages
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if not DAY_PATTERN.match(thread.name):
            return
        forum = thread.parent
        if not isinstance(forum, discord.ForumChannel):
            return
        if await self.config.guild(forum.guild).forum_channel_id() != forum.id:
            return
        summary_thread = await self._ensure_summary_thread(forum)
        await self._update_summary_msg(summary_thread, thread)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return
        thread = message.channel
        if not isinstance(thread, discord.Thread) or not DAY_PATTERN.match(thread.name):
            return
        forum = thread.parent
        if not isinstance(forum, discord.ForumChannel):
            return
        if await self.config.guild(forum.guild).forum_channel_id() != forum.id:
            return
        summary_id = await self.config.guild(forum.guild).summary_thread_id()
        if not summary_id:
            return
        summary_thread = forum.get_thread(summary_id)
        if summary_thread:
            await self._update_summary_msg(summary_thread, thread)