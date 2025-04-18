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
    async def exportchannel(self, ctx, channel: discord.TextChannel, limit: int = 0):
        """Exports the last `limit` messages from a channel to a JSON file. Use 0 for unlimited."""
        
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