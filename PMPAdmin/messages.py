# -*- coding: utf-8 -*-

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