import os
from datetime import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import discord

from PMPAdmin.PMPAdmin import LA_TZ, PMP_GUILD_ID
from PMPAdmin.SupabaseMemberSync import MemberSyncError, SupabaseMemberSync

from .helpers import async_items


class SupabaseMemberSyncTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.project_url = "https://example.supabase.co"
        self.secret_key = "sb_secret_test"
        self.enterContext(patch.dict(os.environ, {
            "SUPABASE_URL": self.project_url + "/",
            "SUPABASE_SECRET_KEY": self.secret_key,
        }))
        self.guild = Mock(id=PMP_GUILD_ID, unavailable=False)
        self.bot = Mock(intents=SimpleNamespace(members=True))
        self.bot.is_ready.return_value = True
        self.bot.get_guild.return_value = self.guild
        self.cog = SupabaseMemberSync(self.bot)
        self.client = self.enterContext(patch.object(aiohttp, "ClientSession"))
        self.session = self.client.return_value.__aenter__.return_value
        self.session.post = MagicMock()
        self.response = self.session.post.return_value.__aenter__.return_value
        self.response.status = 204

    async def test_fetches_full_guild_and_uploads_assigned_role_ids_and_names(self):
        everyone = Mock(id=PMP_GUILD_ID, is_default=Mock(return_value=True))
        producer = SimpleNamespace(id=123456789012345678, name="Producer", is_default=lambda: False)
        self.guild.fetch_members.return_value = async_items(
            SimpleNamespace(id=123456789012345670, roles=[everyone, producer]),
            SimpleNamespace(id=123456789012345671, roles=[everyone]),
        )

        self.assertEqual(await self.cog._sync_members(), 2)
        self.bot.get_guild.assert_called_once_with(PMP_GUILD_ID)
        self.guild.fetch_members.assert_called_once_with(limit=None)
        self.session.post.assert_called_once_with(
            self.project_url + "/rest/v1/rpc/sync_pmp_discord_members",
            headers={"apikey": self.secret_key},
            json={
                "p_guild_id": str(PMP_GUILD_ID),
                "p_members": [
                    {"user_id": "123456789012345670", "roles": [{"id": "123456789012345678", "name": "Producer"}]},
                    {"user_id": "123456789012345671", "roles": []},
                ],
            },
            allow_redirects=False,
        )

    async def test_empty_roster_is_never_sent(self):
        self.guild.fetch_members.return_value = async_items()

        with self.assertRaisesRegex(MemberSyncError, "empty member list"):
            await self.cog._sync_members()
        self.client.assert_not_called()

    async def test_failed_discord_pagination_does_not_upload_partial_roster(self):
        async def failing_fetch():
            yield SimpleNamespace(id=10, roles=[])
            raise discord.HTTPException(SimpleNamespace(status=500, reason="Error"), "Failed")

        self.guild.fetch_members.return_value = failing_fetch()
        with self.assertRaisesRegex(MemberSyncError, "Discord could not list members"):
            await self.cog._sync_members()
        self.client.assert_not_called()

    async def test_requires_member_intent(self):
        self.bot.intents.members = False
        with self.assertRaisesRegex(MemberSyncError, "Server Members Intent"):
            await self.cog._sync_members()
        self.guild.fetch_members.assert_not_called()

    async def test_rejects_non_project_url_before_fetching_members(self):
        with patch.dict(os.environ, {"SUPABASE_URL": self.project_url + "@example.com"}):
            with self.assertRaisesRegex(MemberSyncError, "Use the Supabase project URL"):
                await self.cog._sync_members()
        self.guild.fetch_members.assert_not_called()

    async def test_reports_http_failure_without_reading_supabase_response_body(self):
        self.guild.fetch_members.return_value = async_items(SimpleNamespace(id=10, roles=[]))
        self.response.status = 401
        with self.assertRaisesRegex(MemberSyncError, "HTTP 401"):
            await self.cog._sync_members()
        self.response.text.assert_not_called()

    async def test_nightly_schedule_uses_pacific_midnight_and_logs_failures(self):
        self.assertEqual(self.cog.nightly_sync.time, [time(hour=0, tzinfo=LA_TZ)])
        self.guild.fetch_members.return_value = async_items()
        with self.assertLogs("PMPAdmin.SupabaseMemberSync", level="WARNING") as logs:
            await self.cog.nightly_sync.coro(self.cog)
        self.assertIn("empty member list", logs.output[0])

    async def test_manual_command_reports_success(self):
        self.guild.fetch_members.return_value = async_items(SimpleNamespace(id=10, roles=[]))
        ctx = MagicMock(send=AsyncMock())
        await self.cog.sync_now.callback(self.cog, ctx)
        ctx.send.assert_awaited_once_with("Synced 1 PMP members to Supabase.")
