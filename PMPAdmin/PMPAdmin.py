# -*- coding: utf-8 -*-
import discord
from redbot.core import commands
from datetime import datetime, timezone
from collections import defaultdict

#
# ROLE IDs
#
ROLE_ID_UNVERIFIED = 1335740367026262128

#
# Channel IDs
#
CHANNEL_ID_INTRO = 1173461536031907962
CHANNEL_ID_REMINDER = 1340411672170336398 # Console channel for now
CHANNEL_ID_CHALLENGES = 1270947940843651150
CHANNEL_ID_PRODUCTION_FEEDBACK = 1173461620823961650
CHANNEL_ID_JOURNAL = 1264661701446598658
CHANNEL_ID_BREAKDOWNS = 1334735726360924202
CHANNEL_ID_RULES = 1172411528352387082
CHANNEL_ID_BUILD_A_BEAT = 1271265578556063817
CHANNEL_ID_QOTD = 1319161247576363048
CHANNEL_ID_BOOK_CLUB = 1319161813849342012
CHANNEL_ID_BUY_SELL_TRADE = 1319080558927679600
CHANNEL_ID_TECH_TALK = 1319435010578845716
CHANNEL_ID_GEAR_PLUGINS_DEALS = 1319162149251059754
CHANNEL_ID_ABLETON = 1325594311215153234
CHANNEL_ID_REASON = 1330293070176059392
CHANNEL_ID_WELCOME = 1334290418589761629

#
# Links
#
URL_ONBOARDING = "https://forms.gle/A3NY7NAkuwtw9tsW8"
URL_DISCORD_JOIN = "https://discord.gg/dxBQgPU9Vn"

#
# Large-ish Text Messages
#
DM_MESSAGE_5 = """**Hey there—welcome to Portland Music Producers!**
This Discord server is the online platform for our community. It is a place to share and grow as producers – together. We’re so glad you found us!

Here’s a glimpse of what we’ve got going on:
* **Weekly Calls** – Every Wednesday at 7p we chat production tips, struggles, and what we’re working on.
* **In-Person Meetups** – Every month, at local recording studios.
* **Collaborations & Challenges** – Join weekly creative <#{CHALLENGES_CHANNEL_ID}>, share song ideas, or remix a fellow member’s track!

**Two Steps to Join the Fun** (Complete within 5 days):
1. Fill out our welcome form ({URL_ONBOARDING}).
2. Post your intro in <#{INTRO_CHANNEL_ID}>.

This helps us keep the community filled with folks who are passionate about growing and supporting each other, and gather everyone’s needs so we can offer helpful events, tips, and collabs. We can’t wait to see you dive in!
♥ Portland Music Producers ♥"""

DM_MESSAGE_4 = """**Hey again!**
We hope you’re settling in. Just a quick reminder to:
1. Complete our welcome form  ({URL_ONBOARDING}).
2. Share a bit about yourself in <#{INTRO_CHANNEL_ID}>.

Once you’re a verified member the locked collaboration & feedback channels will open up for you:
* <#{PRODUCTION_FEEDBACK_CHANNEL_ID}> is a safe space to share WIPs, and get constructive critiques to level up your productions.
* Each member gets their own <#{CHANNEL_ID_JOURNAL}> as a personal thread to catalog thoughts, materials, and audio snippets. 
* Got a recent project you can share? Want to learn how to livestream? Make some noise in <#{CHANNEL_ID_BREAKDOWNS}>.

If you have any questions or need help, just let us know. We’re excited to have you on board!
♥ Portland Music Producers ♥"""

DM_MESSAGE_3 = """**Hey again!**
It takes vulnerability and trust to share your art. That’s why in Portland Music Producers we care deeply about nurturing a real sense of community.

Our goal is that everyone here is a participant.

So, share your story in <#{INTRO_CHANNEL_ID}> so we can give you a proper welcome.

Visit <#{CHANNEL_ID_WELCOME}> to see what activities we recommend you start with.

This is your home now too, so explore, make some noise and have fun!
♥ Portland Music Producers ♥"""


DM_MESSAGE_2 = """**Hey there,**
Time’s nearly up. If you haven’t introduced yourself and filled the form, you’ll be removed after tomorrow. We’d hate to see you miss out on:
* <#{CHANNEL_ID_BUILD_A_BEAT}>: A weekly collab project where everyone can add a layer to a track—great for learning and experimenting!
* <#{CHANNEL_ID_QOTD}> (Question of the Day): Thought-provoking daily questions help you get to know yourself and each other.
* <#{CHANNEL_ID_BOOK_CLUB}>: Read and discuss a book that inspires better production and artistry.
* <#{CHANNEL_ID_BUY_SELL_TRADE}>, <#{CHANNEL_ID_TECH_TALK}>, <#{CHANNEL_ID_GEAR_PLUGINS_DEALS}>: Chat about gear and swap items with fellow producers.
* DAW-specific Channels (Ableton, Logic, etc.): Get and give tips tailored to your setup.

**Verification Steps:**
1. ({URL_ONBOARDING}).
2. <#{INTRO_CHANNEL_ID}>.

We truly hope you’ll stick around—there’s so much waiting for you in our community!"""

DM_MESSAGE_1 = """**Hey there,**
You will be kicked from the server if you don’t complete the 2 verification items (intro + form) today. This is an effort to maintain a space that is engaged, safe, and focused on growth.

Thanks for understanding, and we hope you’ll stick around!

If you feel you have completed the requirements and should be verified, just holler at an @admin and let us know!

If you are reading this message and have already been kicked out of the server, know you can always join again: {URL_DISCORD_JOIN}.
"""


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

        message = ""
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
