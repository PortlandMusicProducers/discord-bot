from datetime import timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

import discord
from discord.ext import tasks

from PMPAdmin.PMPAdmin import (
    CHANNEL_ID_CONSOLE,
    CHANNEL_ID_REMINDER,
    DDAY_DATE,
    PMPAdmin,
    ROLE_ID_MEMBER,
    ROLE_ID_UNVERIFIED,
    UNVERIFIED_DM,
    VERIFIED_DM,
    getDaysInServerWithDDAY,
)


class VerificationGracePeriodTests(TestCase):
    def test_deadline_counts_from_dday_or_join_date_whichever_is_later(self):
        now = DDAY_DATE + timedelta(days=8, hours=23)
        for join_offset, days in ((-20, 8), (0, 8), (3, 5)):
            with self.subTest(join_offset=join_offset):
                joined_at = DDAY_DATE + timedelta(days=join_offset)
                self.assertEqual(getDaysInServerWithDDAY(now, joined_at), days)


class OnboardingTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.console = SimpleNamespace(send=AsyncMock())
        self.reminders = SimpleNamespace(send=AsyncMock())
        self.guild = SimpleNamespace(members=[])
        self.bot = Mock()
        self.bot.get_guild.return_value = self.guild
        self.bot.get_channel.side_effect = {
            CHANNEL_ID_CONSOLE: self.console,
            CHANNEL_ID_REMINDER: self.reminders,
        }.get
        with patch.object(tasks.Loop, "start"):
            self.cog = PMPAdmin(self.bot)

    async def test_join_sends_onboarding_dm_to_unverified_member(self):
        member = SimpleNamespace(roles=[], send=AsyncMock())
        await self.cog.on_member_join(member)
        member.send.assert_awaited_once_with(UNVERIFIED_DM)

    async def test_join_skips_members_with_verified_role(self):
        member = SimpleNamespace(roles=[SimpleNamespace(id=ROLE_ID_MEMBER)], send=AsyncMock())
        await self.cog.on_member_join(member)
        member.send.assert_not_awaited()

    async def test_adding_verified_role_sends_dm_and_posts_welcome(self):
        before = SimpleNamespace(roles=[])
        after = SimpleNamespace(
            roles=[SimpleNamespace(id=ROLE_ID_MEMBER)], send=AsyncMock(), display_name="Mina"
        )
        await self.cog.on_member_update(before, after)
        after.send.assert_awaited_once_with(VERIFIED_DM)
        self.reminders.send.assert_awaited_once()
        self.assertIn("Mina", self.reminders.send.await_args.args[0])

    async def test_closed_dms_still_allow_the_public_welcome(self):
        error = discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "DMs closed")
        before = SimpleNamespace(roles=[])
        after = SimpleNamespace(
            roles=[SimpleNamespace(id=ROLE_ID_MEMBER)],
            send=AsyncMock(side_effect=error), display_name="Mina",
        )

        await self.cog.on_member_update(before, after)

        self.console.send.assert_awaited_once()
        self.assertIn("Mina", self.console.send.await_args.args[0])
        self.reminders.send.assert_awaited_once()
        self.assertIn("Mina", self.reminders.send.await_args.args[0])

    async def test_kick_uses_five_day_boundary_and_skips_verified_members(self):
        now = DDAY_DATE + timedelta(days=8)
        for name, days, role_id in (
            ("At deadline", 5, ROLE_ID_UNVERIFIED),
            ("Still has time", 4, ROLE_ID_UNVERIFIED),
            ("Verified", 8, ROLE_ID_MEMBER),
        ):
            self.guild.members.append(SimpleNamespace(
                display_name=name, joined_at=now - timedelta(days=days),
                roles=[SimpleNamespace(id=role_id)], kick=AsyncMock(),
            ))
        at_deadline, still_has_time, verified = self.guild.members

        with patch.object(discord.utils, "utcnow", return_value=now):
            await self.cog.kickUnverified()

        at_deadline.kick.assert_awaited_once()
        still_has_time.kick.assert_not_awaited()
        verified.kick.assert_not_awaited()
        self.console.send.assert_awaited_once()
        self.assertIn("At deadline (5 days)", self.console.send.await_args.args[0])
