from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call, patch

import discord
from redbot.core import Config

from PMPAdmin.ChallengeScraper import DISCORD_LIMIT, ChallengeScraper

from .helpers import async_items


class ChallengeScraperTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = Mock()
        with patch.object(Config, "get_conf", return_value=self.config):
            self.cog = ChallengeScraper(Mock())

    async def test_collects_audio_and_links_by_author_with_duplicates_removed(self):
        audio = SimpleNamespace(
            content_type=None, filename="Sketch.WAV", url="https://cdn.discordapp.com/sketch",
        )
        image = SimpleNamespace(content_type="image/png", filename="cover.png", url="https://example.com/cover")
        messages = (
            SimpleNamespace(
                author=SimpleNamespace(id=1),
                content="https://www.example.com/song https://www.tenor.com/gif https://discord.com/channels/1",
                attachments=[audio, image],
            ),
            SimpleNamespace(
                author=SimpleNamespace(id=1),
                content="https://www.example.com/song https://example.com/art.GIF",
                attachments=[],
            ),
            SimpleNamespace(
                author=SimpleNamespace(id=2), content="https://example.com/second", attachments=[],
            ),
        )
        guild = SimpleNamespace(get_member={1: SimpleNamespace(display_name="zoe")}.get)
        thread = SimpleNamespace(guild=guild, history=Mock(return_value=async_items(*messages)))

        records = await self.cog._collect_urls(thread)
        self.assertEqual(records, [
            ("User 2", ["https://example.com/second"]),
            ("zoe", ["https://cdn.discordapp.com/sketch", "https://www.example.com/song"]),
        ])
        self.assertEqual(
            self.cog._format(records, "DAY 1"),
            "**DAY 1**\nUser 2: [example.com](<https://example.com/second>)\n"
            "zoe: [cdn.discordapp.com](<https://cdn.discordapp.com/sketch>), "
            "[example.com](<https://www.example.com/song>)",
        )
        thread.history.assert_called_once_with(oldest_first=True, limit=None)

    async def test_selects_active_and_archived_day_threads_in_creation_order(self):
        active = SimpleNamespace(name="day 2", created_at=datetime(2025, 2, 2, tzinfo=timezone.utc))
        archived = SimpleNamespace(name="Day 1", created_at=datetime(2025, 2, 1, tzinfo=timezone.utc))
        summary = SimpleNamespace(name="Challenge Summary")
        forum = SimpleNamespace(threads=[active, summary], archived_threads=Mock(return_value=async_items(archived)))
        self.assertEqual(await self.cog._iter_day_threads(forum), [archived, active])

    async def test_long_summary_posts_in_order_without_losing_line_breaks(self):
        first = SimpleNamespace(id=5)
        second = SimpleNamespace(id=6)
        thread = SimpleNamespace(send=AsyncMock(side_effect=[first, second]))
        first_line = "a" * (DISCORD_LIMIT - 1) + "\n"
        second_line = "b" * DISCORD_LIMIT

        result = await self.cog._split_and_send(thread, first_line + second_line)

        self.assertIs(result, first)
        self.assertEqual(thread.send.await_args_list, [call(first_line), call(second_line)])

    async def test_refresh_edits_the_tracked_message_and_keeps_its_id(self):
        saved_mapping = AsyncMock(return_value={"1": 20})
        saved_mapping.set = AsyncMock()
        self.config.guild.return_value.thread_message_map = saved_mapping
        existing = SimpleNamespace(edit=AsyncMock(return_value=SimpleNamespace(id=20)))
        summary = SimpleNamespace(guild=object(), fetch_message=AsyncMock(return_value=existing), send=AsyncMock())
        day = SimpleNamespace(id=1, name="DAY 1", history=Mock(return_value=async_items()))

        await self.cog._update_summary_msg(summary, day)

        summary.fetch_message.assert_awaited_once_with(20)
        existing.edit.assert_awaited_once_with(content="**DAY 1**")
        summary.send.assert_not_awaited()
        saved_mapping.set.assert_awaited_once_with({"1": 20})

    async def test_refresh_replaces_a_deleted_summary_and_stores_its_new_id(self):
        saved_mapping = AsyncMock(return_value={"1": 20, "2": 21})
        saved_mapping.set = AsyncMock()
        self.config.guild.return_value.thread_message_map = saved_mapping
        error = discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Unknown message")
        summary = SimpleNamespace(
            guild=object(), fetch_message=AsyncMock(side_effect=error),
            send=AsyncMock(return_value=SimpleNamespace(id=22)),
        )
        day = SimpleNamespace(id=1, name="DAY 1", history=Mock(return_value=async_items()))

        await self.cog._update_summary_msg(summary, day)

        summary.fetch_message.assert_awaited_once_with(20)
        summary.send.assert_awaited_once_with("**DAY 1**")
        saved_mapping.set.assert_awaited_once_with({"1": 22, "2": 21})
