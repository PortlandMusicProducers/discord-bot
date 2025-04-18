# -*- coding: utf-8 -*-
import discord
import json
import os
from redbot.core import commands

class ExportMessages(commands.Cog):
    """Exports messages from a channel"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def exportchannel(self, ctx, channel: discord.TextChannel):
        """Exports the last `limit` messages from a channel to a JSON file."""
        messages = []
        
        async for message in channel.history(limit=None, oldest_first=True):
            messages.append({
                "author": message.author.name,
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
            })

        # Save to file
        filename = f"{channel.name}_messages.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)

        # Send the file
        await ctx.send("Here is the exported message file:", file=discord.File(filename))

        # Clean up the file
        os.remove(filename)