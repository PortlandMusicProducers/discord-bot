import discord
from redbot.core import commands, Config

REMINDER_MESSAGE = (
    "Hi {display_name}! Please only post audio file attachments in {channel_mention}. "
    "Non-audio messages are removed to keep the channel focused - thanks for understanding!"
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return

        if not message.guild:
            return

        channel_id = await self.config.guild(message.guild).channel_id()
        if channel_id is None or message.channel.id != channel_id:
            return

        # Check attachments for audio files
        has_audio = False
        for a in message.attachments:
            # Prefer content_type if present
            ctype = getattr(a, "content_type", None)
            if ctype and ctype.startswith("audio"):
                has_audio = True
                break
            # Fallback to filename extension
            fname = (getattr(a, "filename", "") or "").lower()
            if any(fname.endswith(ext) for ext in self.AUDIO_EXTS):
                has_audio = True
                break

        if has_audio:
            return

        # Not an audio attachment — delete and send friendly reminder
        try:
            await message.delete()
        except Exception:
            pass

        reminder = REMINDER_MESSAGE.format(
            display_name=message.author.display_name,
            channel_mention=message.channel.mention,
        )

        try:
            await message.author.send(reminder)
        except discord.Forbidden:
            pass
