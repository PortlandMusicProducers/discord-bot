# -*- coding: utf-8 -*-
import discord
import json
import os
import tempfile
from typing import Union
from redbot.core import commands

class ExportMessages(commands.Cog):
    """Exports messages from a channel"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def exportchannel(self, ctx, channel: Union[discord.TextChannel, discord.Thread], limit: int = 0):
        """Exports the last `limit` messages from a channel to a JSON file. Use 0 for unlimited."""
        
        # Resolve an integer based channel id to a thread or channel
        if isinstance(channel, int):
            # Try to fetch it as a thread first, then a channel
            thread = ctx.guild.get_thread(channel)
            if thread:
                channel = thread
            else:
                channel = ctx.guild.get_channel(channel)

        if channel is None:
            await ctx.send("⚠️ Couldn't find the specified channel or thread.")
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