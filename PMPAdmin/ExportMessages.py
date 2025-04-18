# -*- coding: utf-8 -*-
import discord
import json
import os
import tempfile
from redbot.core import commands

class ExportMessages(commands.Cog):
    """Exports messages from a channel"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def exportchannel(self, ctx, channel: str = None, limit: int = 0):
        """Exports the last `limit` messages from a channel to a JSON file. Use 0 for unlimited."""
        
        if channel is None:
            channel_obj = ctx.channel
        else:
            # Try to resolve channel from mention, ID, or name
            channel_id = None

            if channel.startswith("<#") and channel.endswith(">"):
                # Extract ID from channel mention
                channel_id = int(channel[2:-1])
            elif channel.isdigit():
                channel_id = int(channel)
            else:
                # Maybe it's a name? Try to get by name
                found = discord.utils.get(ctx.guild.text_channels, name=channel)
                if found is None:
                    found = discord.utils.get(ctx.guild.threads, name=channel)
                channel_obj = found

            if channel_id:
                channel_obj = ctx.guild.get_thread(channel_id) or ctx.guild.get_channel(channel_id)

            if not channel_obj:
                await ctx.send("❌ Couldn't resolve the channel or thread.")
                return
        
        if limit == 0:
            limit = None
        
        messages = []
        
        async for message in channel.history(limit=limit, oldest_first=True):
            messages.append({
                "author": message.author.name,
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
            })

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8") as tmp:
            json.dump(messages, tmp, ensure_ascii=False, indent=4)
            tmp_path = tmp.name

        # Send the file
        await ctx.send("Here is the exported message file:", file=discord.File(tmp_path))

        # Clean up the file
        os.remove(tmp_path)