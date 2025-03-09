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
CHANNEL_ID_CONSOLE = 1340411672170336398
CHANNEL_ID_GEAR_PLUGINS_DEALS = 1319162149251059754
CHANNEL_ID_INTRO = 1173461536031907962
CHANNEL_ID_JOURNAL = 1264661701446598658
CHANNEL_ID_MODS = 1172413634278854676
CHANNEL_ID_PRODUCTION_FEEDBACK = 1173461620823961650
CHANNEL_ID_QOTD = 1319161247576363048
CHANNEL_ID_REASON = 1330293070176059392
CHANNEL_ID_REMINDER = 1343433464116150373
CHANNEL_ID_RULES = 1172411528352387082
CHANNEL_ID_SUGGESTIONS = 1260465592067162194
CHANNEL_ID_TECH_TALK = 1319435010578845716
CHANNEL_ID_WELCOME = 1334290418589761629
CHANNEL_ID_WHAT_YOU_LISTENING_TO = 1224547549831106650
#
# Links
#
URL_ONBOARDING = "https://forms.gle/A3NY7NAkuwtw9tsW8"
URL_DISCORD_JOIN = "https://discord.gg/dxBQgPU9Vn"

#
# Large-ish Text Messages
#
UNVERIFIED_HEADER = f"""**🔔Unverified Members Reminder:**
To become a verified member, please:
1. Fill out our Google Form ({URL_ONBOARDING}).
2. Post an introduction in <#{CHANNEL_ID_INTRO}>.

If these steps aren't completed, we'll need to remove you from the server to keep things running smoothly. We hope you'll stick around!"""

DM_MESSAGE_5 = f"""**Hey there—welcome to Portland Music Producers!**
This Discord server is the online platform for our community. It is a place to share and grow as producers - together. We're so glad you found us!

Here's a glimpse of what we've got going on:
* **Weekly Calls** - Every Wednesday at 7p we chat production tips, struggles, and what we're working on.
* **In-Person Meetups** - Every month, at local recording studios.
* **Collaborations & Challenges** - Join weekly creative <#{CHANNEL_ID_CHALLENGES}>, share song ideas, or remix a fellow member's track!

**Two Steps to Join the Fun** (Complete within 5 days):
1. Fill out our welcome form ({URL_ONBOARDING}).
2. Post your intro in <#{CHANNEL_ID_INTRO}>.

This helps us keep the community filled with folks who are passionate about growing and supporting each other, and gather everyone's needs so we can offer helpful events, tips, and collabs. We can't wait to see you dive in!
♥ Portland Music Producers ♥"""

DM_MESSAGE_4 = f"""**Hey again!**
We hope you're settling in. Just a quick reminder to:
1. Complete our welcome form  ({URL_ONBOARDING}).
2. Share a bit about yourself in <#{CHANNEL_ID_INTRO}>.

Once you're a verified member the locked collaboration & feedback channels will open up for you:
* <#{CHANNEL_ID_PRODUCTION_FEEDBACK}> is a safe space to share WIPs, and get constructive critiques to level up your productions.
* Each member gets their own <#{CHANNEL_ID_JOURNAL}> as a personal thread to catalog thoughts, materials, and audio snippets. 
* Got a recent project you can share? Want to learn how to livestream? Make some noise in <#{CHANNEL_ID_BREAKDOWNS}>.

If you have any questions or need help, just let us know. We're excited to have you on board!
♥ Portland Music Producers ♥"""

DM_MESSAGE_4_V = f"""**Hey again!**
We hope you're settling in. Now that you're a verified member, the Collaboration & Feedback channels are accessible to you:
* Make your own <#{CHANNEL_ID_JOURNAL}>! These are personal threads where you can be a documentarian of your own work and catalog thoughts, materials, audio snippets, etc., in a semi-public space. They're a great window into the processes of your peers.
* Solicit ideas in <#{CHANNEL_ID_PRODUCTION_FEEDBACK}>, a safe space to share work-in-progress and get constructive critiques that can level up your productions.
* Got a fun project you can share, or technique you can teach?  Want to learn how to livestream? Make some noise in <#{CHANNEL_ID_BREAKDOWNS}>

If you have any questions or need help, just let us know. We're excited to have you on board!
♥ Portland Music Producers ♥"""

DM_MESSAGE_3 = f"""**Hey again!**
It takes vulnerability and trust to share your art. That's why in Portland Music Producers we care deeply about nurturing a real sense of community.

Our goal is that everyone here is a participant.

So, share your story in <#{CHANNEL_ID_INTRO}> so we can give you a proper welcome.

Visit <#{CHANNEL_ID_WELCOME}> to see what activities we recommend you start with.

This is your home now too, so explore, make some noise and have fun!
♥ Portland Music Producers ♥"""

DM_MESSAGE_3_V = f"""**Hey again!**
It takes vulnerability and trust to share your art. That's why in Portland Music Producers we care deeply about nurturing a real sense of community. We believe in an open, safe space where everyone feels welcome to share and grow.

Our goal is that everyone can be a participant. Visit <#{CHANNEL_ID_WELCOME}> to see what activities we recommend you start with.

This is your home now too, so please explore, make some noise and have fun!
♥ Portland Music Producers ♥"""

DM_MESSAGE_2 = f"""**Hey there,**
Time's nearly up. If you haven't introduced yourself and filled the form, you'll be removed after tomorrow. We'd hate to see you miss out on:
* <#{CHANNEL_ID_BUILD_A_BEAT}>: A weekly collab project where everyone can add a layer to a track—great for learning and experimenting!
* <#{CHANNEL_ID_QOTD}> (Question of the Day): Thought-provoking daily questions help you get to know yourself and each other.
* <#{CHANNEL_ID_BOOK_CLUB}>: Read and discuss a book that inspires better production and artistry.
* <#{CHANNEL_ID_BUY_SELL_TRADE}>, <#{CHANNEL_ID_TECH_TALK}>, <#{CHANNEL_ID_GEAR_PLUGINS_DEALS}>: Chat about gear and swap items with fellow producers.
* DAW-specific Channels (#📎ableton, #🍏logic, #🎛pro-tools, etc.): Get and give tips tailored to your setup.

**Verification Steps:**
1. ({URL_ONBOARDING}).
2. <#{CHANNEL_ID_INTRO}>.

We truly hope you'll stick around—there's so much waiting for you in our community!"""

DM_MESSAGE_2_V = f"""**Hey there,**
We hope you've had a chance to poke around the server. Our goal is to be an open, creative, and encouraging space. It can be so incredibly energizing to be surrounded by supportive people who are into the same stuff you are.

Fun ways to mingle?
* Make a move in <#{CHANNEL_ID_BUILD_A_BEAT}>, our weekly collaborative project where each person can add one layer. It's a great way to practice collaborating with others and stimulate the producer-mind, “what is this song calling for?”.
* Answer the <#{CHANNEL_ID_QOTD}>. These thought-provoking daily questions help you get to know yourself and each other.
* Participate in <#{CHANNEL_ID_CHALLENGES}>. These periodic prompts are a fun way to breed creativity, and think outside of the box. Like every other activity everyone is encouraged to participate regardless of experience level."""

DM_MESSAGE_1 = f"""**Hey there,**
You will be kicked from the server if you don't complete the 2 verification items (intro + form) today. This is an effort to maintain a space that is engaged, safe, and focused on growth.

Thanks for understanding, and we hope you'll stick around!

If you feel you have completed the requirements and should be verified, just holler at an @admin and let us know!

If you are reading this message and have already been kicked out of the server, know you can always join again: {URL_DISCORD_JOIN}."""

DM_MESSAGE_1_V = f"""There's a lot of value to uncover here if you know where to look! Here are some last suggestions:
* <#{CHANNEL_ID_WHAT_YOU_LISTENING_TO}>: Take a break from the algorithms and discover music recommended by real life humans.
* DAW-specific channels (#📎ableton, #🍏logic, #🎛pro-tools, etc.). Pro tips to enhance your productions and improve your workflow.
* <#{CHANNEL_ID_BUY_SELL_TRADE}>: Sell or swap gear with fellow producers.

This onboarding messaging is now complete. If you have any questions, holler at a mod, either with a direct message or the @Mod tag - we're here to help.

This community is owned by no one, it is of and for the people. If you have any ideas pop them into <#{CHANNEL_ID_SUGGESTIONS}>. And for anything more substantial or if you want to get involved, holler!
You have found your tribe 🤘.
<3 Portland Music Producers"""

def getVerifiedMembers(guild):
    """Returns a list of verified members and the number of days they've been in the server."""
    now = discord.utils.utcnow()
    verified_members = []

    for member in guild.members:
        if any(role.id == ROLE_ID_MEMBER for role in member.roles):
            join_date = member.joined_at
            verified_members.append((member, join_date))

    # Sort by days in server (newest first)
    return sorted(verified_members, key=lambda x: x[1], reverse=False)

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

def getDMMessageNumberVarName(days_remaining, verified=False):
    message = ""
    if days_remaining >= 5:
        # day 5 has the same messaging for both verified/non-verified
        return "DM_MESSAGE_5"
    elif days_remaining == 4:
        message = "DM_MESSAGE_4"
    elif days_remaining == 3:
        message = "DM_MESSAGE_3"
    elif days_remaining == 2:
        message = "DM_MESSAGE_2"
    elif days_remaining <= 1:
        message = "DM_MESSAGE_1"
    
    if verified:
        message += "_V"

    return message
    
def getDMMessageNumber(days_remaining, verified=False):
    if days_remaining >= 5:
        return DM_MESSAGE_5
    elif days_remaining == 4:
        return DM_MESSAGE_4_V if verified else DM_MESSAGE_4
    elif days_remaining == 3:
        return DM_MESSAGE_3_V if verified else DM_MESSAGE_3
    elif days_remaining == 2:
        return DM_MESSAGE_2_V if verified else DM_MESSAGE_2
    elif days_remaining <= 1:
        return DM_MESSAGE_1_V if verified else DM_MESSAGE_1

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
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]

            verification_channel = self.bot.get_channel(CHANNEL_ID_REMINDER)

            if verification_channel:
                if any(role.id == ROLE_ID_MEMBER for role in added_roles):
                    await verification_channel.send(f"Welcome **{after.display_name}**, now a full member of the community!🎉")

    @tasks.loop(time=DATE_DAILY_SCHEDULE)
    async def dailyCheck(self):
        await self.alertUnverified()
        await self.kickUnverified(5)
        await self.sendOnboardingDMs()
    
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
        await ctx.send(f"Message: {getDMMessageNumberVarName(5, verified)}\n{getDMMessageNumber(5, verified)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(4, verified)}\n{getDMMessageNumber(4, verified)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(3, verified)}\n{getDMMessageNumber(3, verified)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(2, verified)}\n{getDMMessageNumber(2, verified)}")
        await ctx.send(f"Message: {getDMMessageNumberVarName(1, verified)}\n{getDMMessageNumber(1, verified)}")

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

        member_data = []
        message = f"**📝 Unverified Users (Sorted by Join Date) with DDAY: {DDAY_DATE}:**\n\n"
        days_since_dday = (now - DDAY_DATE).days

        for member, join_date in unverified_members:
            # Check if user has posted in Introductions
            intro_posted = member.id in intro_messages
            intro_status = "✅" if intro_posted else "❌"
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            days_remaining = max(0, 5 - days_in_server) 
            message += f"📌 {member.name} - **{(now - join_date).days}** days in server | **{days_remaining}** days remaining | Intro: {intro_status}\n"

        await ctx.send(message)

    async def sendOnboardingDMs(self):
        """Sends a DM onboarding message to verified members during the 5 day intro period"""
        console_channel = self.bot.get_channel(CHANNEL_ID_CONSOLE)

        PMP = self.get_guild()
        if PMP is None:
            print("Could not find guild")
            return
        verified_members = getVerifiedMembers(PMP)

        now = discord.utils.utcnow()
        message = UNVERIFIED_HEADER + "\n"
        success = 0
        failed = 0

        for member, join_date in verified_members:
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            days_remaining = max(0, 5 - days_in_server)
            if days_in_server <= 5:
                #DM Each member with a reminder
                try:
                    await member.send(getDMMessageNumber(days_remaining, True))
                    #await ctx.send(f"Would have sent DM {getDMMessageNumber(days_remaining, True)} to user {member.display_name}")
                    success += 1
                except discord.Forbidden:
                    # Let mods know we couldn't DM someone
                    await console_channel.send(f"⚠️ Could not send onboarding DM to {member.display_name} (DMs closed).")
                    failed += 1

        # Send a summary to the mods
        if success or failed:
            await console_channel.send(f"Sent onboarding DMs. Success: {success} Failed: {failed}")

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
        simulated_dms = ""
        success = 0
        failed = 0

        for member, join_date in unverified_members:
            days_in_server = getDaysInServerWithDDAY(now, join_date)
            days_remaining = max(0, 5 - days_in_server)
            message += f"📌 {member.mention} - you have {days_remaining} days remaining to get verified!\n"

            #simulated_dms += f"Simulated DM to {member.display_name}: With pre-written message: {getDMMessageNumberVarName(days_remaining)}'\n"
            
            #DM Each member with a reminder
            try:
                await member.send(getDMMessageNumber(days_remaining))
                success += 1
            except discord.Forbidden:
                # Let mods know we couldn't DM someone
                await console_channel.send(f"⚠️ Could not DM {member.display_name} (DMs closed).")
                failed += 1

        # Send the verification message in the verification channel
        await verification_channel.send(message)

        # Send a summary to the mods
        await console_channel.send(f"Sent verification DMs. Success: {success} Failed: {failed}")

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
                    # await member.kick(reason=f"Unverified for more than {days_in_server} days")
                    kicked_members.append(f"{member.display_name} ({days_in_server} days)")
                except discord.Forbidden:
                    await console_channel.send(f"⚠️ Could not kick {member.display_name} (missing permissions).")
                except discord.HTTPException:
                    await console_channel.send(f"⚠️ Failed to kick {member.display_name} due to a Discord error.")

        # Send a summary of kicked members
        if kicked_members:
            kicked_list = "\n".join(kicked_members)
            await console_channel.send(f"🦶 **Bot would have kicked the following Unverified Members:**\n```\n{kicked_list}```")
        else:
            await console_channel.send("✅ No members to kick today.")
