import discord
import os
import sys
from redbot.core import commands
from datetime import datetime, timezone
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from messages import *

def getUnverifiedMembers(guild):
    """Returns a list of unverified members and the number of days they've been in the server."""
    now = discord.utils.utcnow()
    unverified_members = []

    for member in guild.members:
        if any(role.id == ROLE_ID_UNVERIFIED for role in member.roles):
            days_in_server = (now - member.joined_at).days if member.joined_at else 0
            unverified_members.append((member, days_in_server))

    # Sort by days in server (oldest first)
    return sorted(unverified_members, key=lambda x: x[1], reverse=True)

def getDMMessageNumberVarName(days_remaining):
    if days_remaining >= 5:
        return "DM_MESSAGE_5"
    elif days_remaining == 4:
        return "DM_MESSAGE_4"
    elif days_remaining == 3:
        return "DM_MESSAGE_3"
    elif days_remaining == 2:
        return "DM_MESSAGE_2"
    elif days_remaining <= 1:
        return "DM_MESSAGE_1"
    
def getDMMessageNumber(days_remaining):
    if days_remaining >= 5:
        return DM_MESSAGE_5
    elif days_remaining == 4:
        return DM_MESSAGE_4
    elif days_remaining == 3:
        return DM_MESSAGE_3
    elif days_remaining == 2:
        return DM_MESSAGE_2
    elif days_remaining <= 1:
        return DM_MESSAGE_1
    
class PMPAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def reportUnverified(self, ctx):
        """List all unverified users and how long they've been in the server and whether they have posted in the intro channel."""
        intro_channel = ctx.guild.get_channel(CHANNEL_ID_INTRO)

        if not intro_channel:
            return await ctx.send("❌ **Introductions channel not found!**")

        unverified_members = getUnverifiedMembers(ctx.guild)
        
        now = datetime.now(timezone.utc)

        # Fetch Introductions channel history once and store user IDs in a set
        intro_messages = set()
        async for message in intro_channel.history(limit=1000):
            intro_messages.add(message.author.id)  # Store only the user IDs

        member_data = []
        message = "**📝 Unverified Users (Sorted by Join Date):**\n\n"

        for member, days_in_server in unverified_members:
            # Check if user has posted in Introductions
            intro_posted = member.id in intro_messages
            intro_status = "✅" if intro_posted else "❌"
            message += f"📌 {member.name} - **{days_in_server} days** in server | Intro: {intro_status}\n"

        await ctx.send(message)

    @commands.command()
    async def alertUnverified(self, ctx):
        """Posts a reminder for all unverified members inside of the reminder channel."""
        channel = self.bot.get_channel(CHANNEL_ID_REMINDER)
        if not channel:
            await ctx.send("⚠️ Error: Could not find the alert channel.")
            return

        unverified_members = getUnverifiedMembers(ctx.guild)

        if not unverified_members:
            await channel.send("✅ No unverified members to remind!")
            return

        message = UNVERIFIED_MESSAGE + "\n"
        simulated_dms = ""

        for member, days_in_server in unverified_members:
            days_remaining = max(0, 5 - days_in_server)  # Countdown from 5 days
            message += f"📌 {member.mention} - you have {days_remaining} days remaining to get verified!\n"

            simulated_dms += f"Simulated DM to {member.display_name}: With pre-written message : {getDMMessageNumberVarName(days_remaining)}'\n"
            
            #DM Each member with a reminder
            '''
            try:
                await member.send(getDMMessageNumber(days_remaining))
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not DM {member.display_name} (DMs closed).")
            '''

        # Send the message in the alert channel
        #await channel.send(message)
        await ctx.send(message)
        await ctx.send(f"🔹 **Simulated DMs:**\n```\n{simulated_dms}```")
        await ctx.send(f"Message: {getDMMessageNumberVarName(5)}\n{getDMMessageNumber(5)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(4)}\n{getDMMessageNumber(4)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(3)}\n{getDMMessageNumber(3)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(2)}\n{getDMMessageNumber(2)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(1)}\n{getDMMessageNumber(1)}")

    @commands.command()
    @commands.has_permissions(kick_members=True)  # Requires kick permissions
    async def kickUnverified(self, ctx, days_max_before_kick: int = 5):
        """Kicks all Unverified users who have been in the server for more than the specified number of days (default: 5)."""
        unverified_members = getUnverifiedMembers(ctx.guild)

        if not unverified_members:
            await ctx.send("✅ No unverified members to kick!")
            return

        kicked_members = []
        for member, days_in_server in unverified_members:
            if days_in_server > days_max_before_kick:
                try:
                    # await member.kick(reason=f"Unverified for more than {days} days")
                    kicked_members.append(f"{member.display_name} ({days_in_server} days)")
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Could not kick {member.display_name} (missing permissions).")
                except discord.HTTPException:
                    await ctx.send(f"⚠️ Failed to kick {member.display_name} due to a Discord error.")

        # Send a summary of kicked members
        if kicked_members:
            kicked_list = "\n".join(kicked_members)
            await ctx.send(f"🔨 **Simulation Would have Kicked Unverified Members:**\n```\n{kicked_list}```")
        else:
            await ctx.send("✅ No members were kicked.")
            
async def setup(bot):
    cog = PMPAdmin(bot)
    await bot.add_cog(cog)
