import discord
from redbot.core import commands
from datetime import datetime, timezone
from collections import defaultdict

UNVERIFIED_ROLE_ID = 1335740367026262128
INTRO_CHANNEL_ID = 1173461536031907962
REMINDER_CHANNEL_ID = 1340411672170336398
DM_MESSAGE = "A heartfelt DM message that inspires user."

def getUnverifiedMembers(guild):
    """Returns a list of unverified members and their days in the server."""
    now = discord.utils.utcnow()
    unverified_members = []

    for member in guild.members:
        if any(role.id == UNVERIFIED_ROLE_ID for role in member.roles):
            days_in_server = (now - member.joined_at).days if member.joined_at else 0
            unverified_members.append((member, days_in_server))

    # Sort by days in server (oldest first)
    return sorted(unverified_members, key=lambda x: x[1], reverse=True)

class PMPAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def reportUnverified(self, ctx):
        """List unverified users and how long they've been in the server and whether they have posted in the intro channel."""
        intro_channel = ctx.guild.get_channel(INTRO_CHANNEL_ID)

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
        """Posts a reminder for unverified members."""
        channel = self.bot.get_channel(REMINDER_CHANNEL_ID)
        if not channel:
            await ctx.send("⚠️ Error: Could not find the alert channel.")
            return

        unverified_members = getUnverifiedMembers(ctx.guild)

        if not unverified_members:
            await channel.send("✅ No unverified members to remind!")
            return

        message = "**🔔 Reminder for Unverified Members:**\nTODO TODO\n"
        simulated_dms = ""

        for member, days_in_server in unverified_members:
            days_remaining = max(0, 5 - days_in_server)  # Countdown from 5 days
            message += f"📌 {member.mention} - **{days_remaining} days remaining to get verified**\n"

            simulated_dms += f"Simulated DM to {member.display_name}: {DM_MESSAGE}'\n"
            #DM Each member with a reminder
            '''
            try:
                await member.send(DM_MESSAGE)
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not DM {member.display_name} (DMs closed).")
            '''

        # Send the message in the alert channel
        #await channel.send(message)
        await ctx.send(message)
        await ctx.send(f"🔹 **Simulated DMs:**\n```\n{simulated_dms}```")

    @commands.command()
    @commands.has_permissions(kick_members=True)  # Requires kick permissions
    async def kickUnverified(self, ctx, days: int = 5):
        """Kicks all Unverified users who have been in the server for more than the specified number of days (default: 5)."""
        unverified_members = getUnverifiedMembers(ctx.guild)

        if not unverified_members:
            await ctx.send("✅ No unverified members to kick!")
            return

        kicked_members = []
        for member, days_in_server in unverified_members:
            if days_in_server > days:
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
