import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from PMPAdmin import ExportMessages

from .helpers import async_items


class ExportMessagesTests(IsolatedAsyncioTestCase):
    async def test_exports_unicode_json_and_removes_the_temporary_file(self):
        created_at = datetime(2025, 2, 24, 12, tzinfo=timezone.utc)
        messages = [
            SimpleNamespace(author=SimpleNamespace(name="Zoë"), content="New sketch 🎵", created_at=created_at),
            SimpleNamespace(author=SimpleNamespace(name="Mina"), content="Sounds good", created_at=created_at),
        ]
        channel = SimpleNamespace(history=Mock(return_value=async_items(*messages)))
        cog = ExportMessages(Mock())

        async def read_upload(_reply, *, file):
            path = Path(file.fp.name)
            self.addCleanup(path.unlink, missing_ok=True)
            try:
                self.assertTrue(file.filename.endswith(".json"))
                self.assertEqual(json.load(file.fp), [
                    {"author": "Zoë", "content": "New sketch 🎵", "timestamp": "2025-02-24T12:00:00+00:00"},
                    {"author": "Mina", "content": "Sounds good", "timestamp": "2025-02-24T12:00:00+00:00"},
                ])
            finally:
                file.close()

        ctx = SimpleNamespace(send=AsyncMock(side_effect=read_upload))
        await cog.exportchannel.callback(cog, ctx, channel)
        channel.history.assert_called_once_with(limit=None, oldest_first=True)
        ctx.send.assert_awaited_once()
        self.assertFalse(Path(ctx.send.await_args.kwargs["file"].fp.name).exists())

    async def test_passes_a_positive_limit_to_channel_history(self):
        channel = SimpleNamespace(history=Mock(return_value=async_items()))
        cog = ExportMessages(Mock())

        async def close_upload(_reply, *, file):
            file.close()

        ctx = SimpleNamespace(send=AsyncMock(side_effect=close_upload))
        await cog.exportchannel.callback(cog, ctx, channel, limit=7)
        channel.history.assert_called_once_with(limit=7, oldest_first=True)
