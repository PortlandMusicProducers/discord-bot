# -*- coding: utf-8 -*-
import discord
from redbot.core import commands
from discord.ext import tasks
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo 
from collections import defaultdict

# Define DDAY as Midnight on Feb 24 UTC
DDAY_DATE = datetime(2025, 2, 24, 0, 0, 0, tzinfo=timezone.utc)

LA_TZ = ZoneInfo("America/Los_Angeles")
DATE_DAILY_SCHEDULE = time(hour=9, minute=0, tzinfo=LA_TZ)

#
# ROLE IDs
#
ROLE_ID_MEMBER = 1330786935542775808
ROLE_ID_UNVERIFIED = 1335740367026262128

#
# Channel IDs
#
CHANNEL_ID_ABLETON = 1325594311215153234
CHANNEL_ID_BOOK_CLUB = 1319161813849342012
CHANNEL_ID_BREAKDOWNS = 1334735726360924202
CHANNEL_ID_BUILD_A_BEAT = 1271265578556063817
CHANNEL_ID_BUY_SELL_TRADE = 1319080558927679600
CHANNEL_ID_CHALLENGES = 1270947940843651150
CHANNEL_ID_COLLABS = 1352158084750901328
CHANNEL_ID_CONSOLE = 1340411672170336398
CHANNEL_ID_GEAR_PLUGINS_DEALS = 1319162149251059754
CHANNEL_ID_INTRO = 1173461536031907962
CHANNEL_ID_JOURNAL = 1264661701446598658
CHANNEL_ID_MODS = 1172413634278854676
CHANNEL_ID_PRODUCTION_FEEDBACK = 1173461620823961650
CHANNEL_ID_ROLE_ASSIGNMENT = 1436888687110524969
CHANNEL_ID_QOTD = 1319161247576363048
CHANNEL_ID_REASON = 1330293070176059392
CHANNEL_ID_REMINDER = 1343433464116150373
CHANNEL_ID_RULES = 1172411528352387082
CHANNEL_ID_SESSIONBREAKDOWNS = 1334735726360924202
CHANNEL_ID_SKETCHPAD = 1469945140792787088
CHANNEL_ID_SUGGESTIONS = 1260465592067162194
CHANNEL_ID_TECH_TALK = 1319435010578845716
CHANNEL_ID_WELCOME = 1334290418589761629
CHANNEL_ID_WHAT_YOU_LISTENING_TO = 1224547549831106650

#
# Links
#
URL_ONBOARDING = "https://forms.gle/A3NY7NAkuwtw9tsW8"

#
# Large-ish Text Messages
#
UNVERIFIED_HEADER = f"""**🔔To become a verified member, please:**
1. Fill out our [welcome form]({URL_ONBOARDING}).
2. Post an introduction in <#{CHANNEL_ID_INTRO}>.
3. Mark your genres, tools, and skills in <#{CHANNEL_ID_ROLE_ASSIGNMENT}>

Once those steps are complete, an admin will manually verify you, and you will gain full access to all channels.
"""

UNVERIFIED_DM = f"""
**Hey there, welcome to Portland Music Producers!**
This Discord is the home base for our community — a place to connect, grow, and actually finish music.

**Activities**:
* **[Weekly Touchbase](<https://discord.com/events/1172411527870034000/1381835513400393799>)** – What you're working on + life updates | 🗓️Every Wednesday at 7p.
* **[Lyric Writing Circle](<https://discord.com/events/1172411527870034000/1380957155011596410>)** – Sharpen your writing with guided exercises | 🗓️Every Saturday at 10a.
* **Challenges** – Join and suggest creative #🎢challenges (e.g. “Make a song using food sounds”). 
* **In-Person Meetups** – Real humans, real studios!

**Three steps to join the fun** (Required to complete within 5 days):
1. Fill out our [welcome form]({URL_ONBOARDING}).
2. Post an introduction in <#{CHANNEL_ID_INTRO}>.
3. Mark your genres, tools, and skills in <#{CHANNEL_ID_ROLE_ASSIGNMENT}>

This helps us keep the community full of people who care about the craft and show up to grow together.
Let's make some records! 🎶
♥ Portland Music Producers ♥
"""

VERIFIED_DM = f"""
**You're in. Welcome to Portland Music Producers. 🎶**
Now that you're verified, the full community is open to you: collaboration, feedback, and everything in between.

It takes vulnerability to put yourself out there. That's why we care deeply about building a real sense of community — a space where people lift each other up, and grow together, despite our differences.

The goal is for everyone to participate, so don't be shy, post something!

**Here are some great places to start:**
 • <#{CHANNEL_ID_SKETCHPAD}> – Quickly share whatever you're cookin' up
 • <#{CHANNEL_ID_PRODUCTION_FEEDBACK}> – Get constructive feedback to level up
 • <#{CHANNEL_ID_COLLABS}> – Find people to make music with
 • <#{CHANNEL_ID_SESSIONBREAKDOWNS}> – Share or request breakdowns of tracks
 • <#{CHANNEL_ID_JOURNAL}> – Your personal thread to capture ideas, progress, and inspiration

Check out <#{CHANNEL_ID_WELCOME}> for more ways to get involved. If you have any questions or need help, just holler.
This is your home now too — so explore, make some noise, and have fun.
♥ Portland Music Producers ♥
"""


def getUnverifiedMembers(guild):
    """Returns a list of unverified members and the number of days they've been in the server."""
    now = discord.utils.utcnow()
    unverified_members = []

    for member in guild.members:
        if any(role.id == ROLE_ID_UNVERIFIED for role in member.roles):
            join_date = member.joined_at
            unverified_members.append((member, join_date))

    # Sort by days in server (oldest first)
    return sorted(unverified_members, key=lambda x: x[1], reverse=True)

def getDaysInServerWithDDAY(now, join_date):
    days_in_server = 0
    if join_date < DDAY_DATE:
        days_in_server = (now - DDAY_DATE).days
    else:
        days_in_server = (now - join_date).days
    return days_in_server

class PMPAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dailyCheck.start()
    
    def get_guild(self):
        return self.bot.get_guild(1172411527870034000)
    
    def cog_unload(self):
        self.dailyCheck.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if any(role.id == ROLE_ID_MEMBER for role in member.roles):
            return

        console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)
        try:
            await member.send(UNVERIFIED_DM)
        except discord.Forbidden:
            if console_channel:
                await console_channel.send(f"Could not send unverified DM to {member.display_name} (DMs closed).")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            verification_channel = self.bot.get_channel(CHANNEL_ID_REMINDER)
            console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)

            if any(role.id == ROLE_ID_MEMBER for role in added_roles):
                try:
                    await after.send(VERIFIED_DM)
                except discord.Forbidden:
                    if console_channel:
                        await console_channel.send(f"Could not send verified DM to {after.display_name} (DMs closed).")

                if verification_channel:
                    await verification_channel.send(f"Welcome **{after.display_name}**, now a full member of the community!🎉")

    @tasks.loop(time=DATE_DAILY_SCHEDULE)
    async def dailyCheck(self):
        await self.alertUnverified()
        await self.kickUnverified(5)
    
    @dailyCheck.before_loop
    async def before_dailyCheck(self):
        console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)
        if console_channel:
            await console_channel.send("🤖 Registered daily verification check at 9am")

    @commands.command()
    async def testMessaging(self, ctx):
        await self.simulateMessages(ctx, False)

    @commands.command()
    async def testMessaging2(self, ctx):
        await self.simulateMessages(ctx, True)        

    @commands.command()
    async def simulateMessages(self, ctx, verified=False):
        """Prints all of the messages we have to check for formatting"""
        await ctx.send(UNVERIFIED_HEADER)
        await ctx.send(f"Message: {'VERIFIED_DM' if verified else 'UNVERIFIED_DM'}\n{VERIFIED_DM if verified else UNVERIFIED_DM}")

    @commands.command()
    async def reportUnverified(self, ctx):
        """List all unverified users and how long they've been in the server and whether they have posted in the intro channel."""
        intro_channel = ctx.guild.get_channel(CHANNEL_ID_INTRO)

        if not intro_channel:
            return await ctx.send("❌ **Introductions channel not found!**")

        unverified_members = getUnverifiedMembers(ctx.guild)
        
        now = discord.utils.utcnow()

        # Fetch Introductions channel history once and store user IDs in a set
        intro_messages = set()
        async for message in intro_channel.history(limit=1000):
            intro_messages.add(message.author.id)  # Store only the user IDs

        message = f"**📝 Unverified Users (Sorted by Join Date) with DDAY: {DDAY_DATE}:**\n\n"

        for member, join_date in unverified_members:
            # Check if user has posted in Introductions
            intro_posted = member.id in intro_messages
            intro_status = "✅" if intro_posted else "❌"
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            days_remaining = max(0, 5 - days_in_server) 
            message += f"📌 {member.name} - **{(now - join_date).days}** days in server | **{days_remaining}** days remaining | Intro: {intro_status}\n"

        await ctx.send(message)

    async def alertUnverified(self):
        """Posts a reminder for all unverified members inside of the reminder channel."""
        verification_channel = self.bot.get_channel(CHANNEL_ID_REMINDER)
        console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)

        PMP = self.get_guild()
        if PMP is None:
            print("Could not find guild")
            return
        unverified_members = getUnverifiedMembers(PMP)

        if not unverified_members:
            await console_channel.send("✅ No unverified members to remind!")
            return

        now = discord.utils.utcnow()
        message = UNVERIFIED_HEADER + "\n"
        for member, join_date in unverified_members:
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            days_remaining = max(0, 5 - days_in_server)
            message += f"📌 {member.mention} - you have {days_remaining} days remaining to get verified!\n"

        # Send the verification message in the verification channel
        await verification_channel.send(message)


    # This used to be a command, but at the end of the day, admins don't need to call it manually, so note the removal of the
    # context parameter.
    async def kickUnverified(self, days_max_before_kick: int = 5):
        """Kicks all Unverified users who have been in the server for more than the specified number of days (default: 5)."""
        PMP = self.get_guild()
        if PMP is None:
            print("Could not find guild")
            return
        
        unverified_members = getUnverifiedMembers(PMP)

        # Assume the channel always exists
        console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)

        now = discord.utils.utcnow()
        kicked_members = []

        for member, join_date in unverified_members:
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            if days_in_server >= days_max_before_kick:
                try:
                    await member.kick(reason=f"Unverified for more than {days_in_server} days")
                    kicked_members.append(f"{member.display_name} ({days_in_server} days)")
                except discord.Forbidden:
                    await console_channel.send(f"⚠️ Could not kick {member.display_name} (missing permissions).")
                except discord.HTTPException:
                    await console_channel.send(f"⚠️ Failed to kick {member.display_name} due to a Discord error.")

        # Send a summary of kicked members
        if kicked_members:
            kicked_list = "\n".join(kicked_members)
            await console_channel.send(f"🦶 **Bot kicked the following Unverified Members:**\n```\n{kicked_list}```")
        else:
            await console_channel.send("✅ No members to kick today.")
