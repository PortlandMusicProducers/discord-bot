import importlib
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from PMPAdmin import TalkModerator


class TalkModeratorTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.guild = SimpleNamespace(id=1)
        self.config = Mock()
        self.config.guild.return_value.channel_id = AsyncMock(return_value=10)
        module = importlib.import_module(TalkModerator.__module__)
        with patch.object(module.Config, "get_conf", return_value=self.config):
            self.cog = TalkModerator(Mock())
        self.delay = self.enterContext(patch.object(module.asyncio, "sleep", new_callable=AsyncMock))
        self.audio = SimpleNamespace(filename="sketch.WAV", content_type=None)
        self.reminder = SimpleNamespace(delete=AsyncMock())
        self.channel = SimpleNamespace(id=10, send=AsyncMock(return_value=self.reminder))

    def message(self, **overrides):
        fields = dict(
            guild=self.guild, channel=self.channel, content="   ", stickers=[],
            author=SimpleNamespace(bot=False, mention="<@25>"), attachments=[self.audio],
            delete=AsyncMock(),
        )
        return SimpleNamespace(**(fields | overrides))

    async def test_accepts_one_audio_file_by_extension_or_content_type(self):
        for attachment in (self.audio, SimpleNamespace(filename="song.bin", content_type="audio/flac")):
            with self.subTest(attachment=attachment):
                message = self.message(attachments=[attachment])
                await self.cog.on_message(message)
                message.delete.assert_not_awaited()
        self.channel.send.assert_not_awaited()

    async def test_rejects_text_stickers_and_wrong_attachment_counts_or_types(self):
        image = SimpleNamespace(filename="cover.png", content_type="image/png")
        for overrides in (
            {"content": "My sketch"}, {"stickers": [object()]}, {"attachments": []},
            {"attachments": [self.audio, image]}, {"attachments": [image]},
        ):
            with self.subTest(overrides=overrides):
                self.channel.send.reset_mock()
                self.reminder.delete.reset_mock()
                self.delay.reset_mock()
                message = self.message(**overrides)
                await self.cog.on_message(message)
                message.delete.assert_awaited_once()
                self.channel.send.assert_awaited_once()
                self.assertIn("<@25>", self.channel.send.await_args.args[0])
                self.delay.assert_awaited_once_with(20)
                self.reminder.delete.assert_awaited_once()

    async def test_ignores_bots_private_messages_and_other_channels(self):
        other_channel = SimpleNamespace(id=11, send=AsyncMock())
        for overrides in (
            {"author": SimpleNamespace(bot=True)}, {"guild": None}, {"channel": other_channel},
        ):
            with self.subTest(overrides=overrides):
                message = self.message(content="Text only", **overrides)
                await self.cog.on_message(message)
                message.delete.assert_not_awaited()
        self.channel.send.assert_not_awaited()
        other_channel.send.assert_not_awaited()

    async def test_rechecks_the_edited_version_of_a_message(self):
        before = self.message()
        after = self.message(content="Added a caption")
        await self.cog.on_message_edit(before, after)
        before.delete.assert_not_awaited()
        after.delete.assert_awaited_once()
