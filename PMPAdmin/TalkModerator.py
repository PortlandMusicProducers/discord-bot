import asyncio
import discord
from redbot.core import commands, Config

REMINDER_MESSAGE = (
    "🎶Bleep boop🎶 Hi {user_mention}! {channel_mention} is designed for quick posting and listening — single audio files only (no message text). "
    "Want to add notes or get feedback? Post (or forward your sketch) to <#1264661701446598658> or <#1173461620823961650>. "
    "Please try again — we're excited to hear it!"
)

class TalkModerator(commands.Cog):
    """Enforce audio-only posts in a configured channel using Red's Config.

    Commands:
    - setchannel <#channel>: set the channel to monitor for this guild
    - setchannel (no args): show current configured channel
    - clearchannel: remove configuration for this guild
    """

    AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac")

    def __init__(self, bot):
        self.bot = bot
        # Use Red's Config to store per-guild channel_id (same pattern as YoutubePlaylistListener)
        self.config = Config.get_conf(self, identifier=4072712030, force_registration=True)
        self.config.register_guild(channel_id=None)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setchannel(self, ctx, channel: discord.TextChannel = None):
        """Set or show the channel where TalkModerator enforces audio-only posts.

        Usage:
          `setchannel #channel`  -> set the channel
          `setchannel`           -> show current channel
        Requires `Manage Guild` permission.
        """
        gid = str(ctx.guild.id)
        if channel is None:
            ch_id = await self.config.guild(ctx.guild).channel_id()
            if ch_id:
                return await ctx.send(f"Currently enforcing channel: <#{ch_id}>")
            return await ctx.send("No channel configured. Use `setchannel #channel` to set one.")

        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"TalkModerator channel set to {channel.mention}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def clearchannel(self, ctx):
        """Clear the configured channel for this guild."""
        ch_id = await self.config.guild(ctx.guild).channel_id()
        if ch_id is not None:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("TalkModerator channel cleared.")
        else:
            await ctx.send("No channel configured.")

    async def _enforce_audio_only(self, message: discord.Message) -> bool:
        """
        Check if message violates audio-only rule and enforce if needed.
        Returns True if enforcement action was taken, False otherwise.
        """
        # Ignore bots and DMs
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return False

        if not message.guild:
            return False

        channel_id = await self.config.guild(message.guild).channel_id()
        if channel_id is None or message.channel.id != channel_id:
            return False

        # Check if message has text content (stripped of whitespace)
        has_text = bool(message.content.strip())

        # Check if message has stickers
        has_stickers = bool(message.stickers)

        # If no text and no stickers, message is valid
        if not has_text and not has_stickers:
            return False

        # Invalid message — delete and send channel reminder
        try:
            await message.delete()
        except Exception:
            pass

        reminder = REMINDER_MESSAGE.format(
            user_mention=message.author.mention,
            channel_mention=message.channel.mention,
        )

        try:
            reminder_msg = await message.channel.send(f"{reminder}")
            # Delete the reminder after 20 seconds
            await asyncio.sleep(20)
            await reminder_msg.delete()
        except Exception:
            pass

        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._enforce_audio_only(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self._enforce_audio_only(after)
