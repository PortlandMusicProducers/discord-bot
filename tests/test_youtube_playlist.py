from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

from googleapiclient.errors import HttpError
from httplib2 import Response
from redbot.core import Config

from PMPAdmin import YoutubePlaylistListener


VIDEO_ID = "dQw4w9WgXcQ"
SEASON = "Winter 2024 - What Are You Listening To?"


class PlaylistNamingTests(TestCase):
    def test_season_and_year_for_every_month(self):
        expected = (
            "Winter 2024", "Winter 2024", "Spring 2025", "Spring 2025", "Spring 2025",
            "Summer 2025", "Summer 2025", "Summer 2025", "Fall 2025", "Fall 2025",
            "Fall 2025", "Winter 2025",
        )
        for month, season in enumerate(expected, start=1):
            with self.subTest(month=month):
                date = datetime(2025, month, 1, tzinfo=timezone.utc)
                self.assertEqual(
                    YoutubePlaylistListener._season_year(date), f"{season} - What Are You Listening To?"
                )


class YoutubePlaylistTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        config = Mock()
        self.guild_config = config.guild.return_value
        for name, value in (
            ("channel_id", 10), ("playlists", {}), ("added_video_ids", []), ("contributors", {}),
        ):
            setting = AsyncMock(return_value=value)
            setting.set = AsyncMock()
            setattr(self.guild_config, name, setting)

        self.service = Mock()
        self.service.playlists.return_value.insert.return_value.execute.return_value = {"id": "playlist-1"}
        self.insert_video = self.service.playlistItems.return_value.insert
        bot = Mock(wait_until_ready=AsyncMock())
        with (
            patch.object(Config, "get_conf", return_value=config),
            patch.object(YoutubePlaylistListener, "_build_youtube_service", return_value=self.service),
        ):
            self.cog = YoutubePlaylistListener(bot)
            startup = bot.loop.create_task.call_args.args[0]
            await startup

        self.message = SimpleNamespace(
            author=SimpleNamespace(id=25, bot=False), guild=SimpleNamespace(id=1, name="PMP"),
            channel=SimpleNamespace(id=10), add_reaction=AsyncMock(),
            content=f"https://youtu.be/{VIDEO_ID} https://www.youtube.com/watch?v={VIDEO_ID}",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

    async def test_creates_seasonal_playlist_and_records_a_repeated_link_once(self):
        with self.assertLogs("red.youtubeplaylist", level="INFO"):
            await self.cog.on_message(self.message)

        create_playlist = self.service.playlists.return_value.insert
        create_playlist.assert_called_once()
        self.assertEqual(create_playlist.call_args.kwargs["body"]["snippet"]["title"], SEASON)
        self.guild_config.playlists.set.assert_awaited_once_with({SEASON: "playlist-1"})
        self.insert_video.assert_called_once_with(part="snippet", body={
            "snippet": {
                "playlistId": "playlist-1",
                "resourceId": {"kind": "youtube#video", "videoId": VIDEO_ID},
            },
        })
        self.guild_config.added_video_ids.set.assert_awaited_once_with([VIDEO_ID])
        self.guild_config.contributors.set.assert_awaited_once_with({"25": 1})
        self.message.add_reaction.assert_awaited_once()

    async def test_previously_recorded_video_does_not_change_playlist_or_metadata(self):
        self.guild_config.added_video_ids.return_value = [VIDEO_ID]
        await self.cog.on_message(self.message)

        self.service.playlists.assert_not_called()
        self.insert_video.assert_not_called()
        self.guild_config.added_video_ids.set.assert_not_awaited()
        self.guild_config.contributors.set.assert_not_awaited()
        self.message.add_reaction.assert_not_awaited()

    async def test_missing_video_reuses_playlist_without_recording_a_contribution(self):
        self.guild_config.playlists.return_value = {SEASON: "playlist-1"}
        self.message.content = f"https://youtu.be/{VIDEO_ID}"
        self.insert_video.return_value.execute.side_effect = HttpError(
            Response({"status": "404", "reason": "Not Found"}), b'{"error": {"message": "Video not found"}}',
        )

        with self.assertLogs("red.youtubeplaylist", level="WARNING"):
            await self.cog.on_message(self.message)

        self.service.playlists.assert_not_called()
        self.insert_video.assert_called_once()
        self.guild_config.added_video_ids.set.assert_not_awaited()
        self.guild_config.contributors.set.assert_not_awaited()
        self.message.add_reaction.assert_not_awaited()

    async def test_ignores_non_monitoring_channel(self):
        self.message.channel.id = 11
        await self.cog.on_message(self.message)

        self.guild_config.added_video_ids.assert_not_awaited()
        self.insert_video.assert_not_called()
        self.message.add_reaction.assert_not_awaited()
