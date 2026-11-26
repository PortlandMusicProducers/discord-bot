import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call, patch

import discord

from PMPAdmin import RoleAssignment


class RoleAssignmentTests(IsolatedAsyncioTestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.module_path = str(Path(directory, "PMPAdmin", "RoleAssignment.py"))
        self.bot = Mock(user=SimpleNamespace(id=100))
        self.guild = Mock(id=1)
        self.bot.get_guild.return_value = self.guild
        self.ctx = SimpleNamespace(guild=self.guild, send=AsyncMock())
        self.role = SimpleNamespace(id=30, mention="<@&30>")
        self.guild.get_role.return_value = self.role
        self.cog = self.open_cog()

    def open_cog(self):
        module = importlib.import_module(RoleAssignment.__module__)
        with patch.object(module, "__file__", self.module_path):
            cog = RoleAssignment(self.bot)
        self.addCleanup(cog.cog_unload)
        return cog

    async def configure_mapping(self):
        await self.cog.roleassign.callback(self.cog, self.ctx, "DAW", "10")
        await self.cog.rolemap.callback(self.cog, self.ctx, "add", "daw", "🎵", self.role)

    async def test_mapping_survives_reopening_the_database(self):
        await self.configure_mapping()
        self.cog.cog_unload()
        self.cog = self.open_cog()

        await self.cog.roleassign.callback(self.cog, self.ctx)
        self.assertIn("daw: 10", self.ctx.send.await_args.args[0])
        await self.cog.rolemap.callback(self.cog, self.ctx, "list", "DAW")
        self.assertIn("🎵 -> <@&30>", self.ctx.send.await_args.args[0])
        self.assertEqual(self.cog.tracked_messages, {"10"})

    async def test_replacing_and_removing_category_updates_tracked_messages(self):
        await self.configure_mapping()
        await self.cog.roleassign.callback(self.cog, self.ctx, "daw", "11")
        self.assertEqual(self.cog.tracked_messages, {"11"})

        await self.cog.roleassign.callback(self.cog, self.ctx, "remove", "DAW")
        self.assertEqual(self.cog.tracked_messages, set())
        await self.cog.roleassign.callback(self.cog, self.ctx)
        self.assertIn("No role assignment messages", self.ctx.send.await_args.args[0])

    async def test_removed_mapping_stays_removed_after_reopening(self):
        await self.configure_mapping()
        await self.cog.rolemap.callback(self.cog, self.ctx, "remove", "daw", "🎵")
        self.cog.cog_unload()
        self.cog = self.open_cog()

        await self.cog.rolemap.callback(self.cog, self.ctx, "list", "daw")
        self.ctx.send.assert_awaited_with("No emoji mappings for that message.")

    async def test_migrate_copies_mappings_to_destination(self):
        await self.configure_mapping()
        await self.cog.roleassign.callback(self.cog, self.ctx, "genre", "11")
        await self.cog.rolemigrate.callback(self.cog, self.ctx, "DAW", "genre")

        for category in ("daw", "genre"):
            with self.subTest(category=category):
                await self.cog.rolemap.callback(self.cog, self.ctx, "list", category)
                self.assertIn("🎵 -> <@&30>", self.ctx.send.await_args.args[0])

    async def test_populate_uses_unicode_and_custom_emoji_reactions(self):
        await self.configure_mapping()
        custom_emoji = "<:daw:123456789012345678>"
        await self.cog.rolemap.callback(self.cog, self.ctx, "add", "daw", custom_emoji, self.role)
        message = SimpleNamespace(add_reaction=AsyncMock())
        inaccessible = SimpleNamespace(fetch_message=AsyncMock(side_effect=discord.NotFound(
            SimpleNamespace(status=404, reason="Not Found"), "Unknown message"
        )))
        accessible = SimpleNamespace(fetch_message=AsyncMock(return_value=message))
        self.guild.text_channels = [inaccessible, accessible]

        await self.cog.rolepopulate.callback(self.cog, self.ctx, "DAW")

        inaccessible.fetch_message.assert_awaited_once_with(10)
        accessible.fetch_message.assert_awaited_once_with(10)
        reactions = [reaction.args[0] for reaction in message.add_reaction.await_args_list]
        self.assertCountEqual(reactions, ["🎵", discord.PartialEmoji.from_str(custom_emoji)])
        self.ctx.send.assert_awaited_with("Populated 1 message(s).")

    async def test_reaction_add_and_remove_update_the_member_role(self):
        await self.configure_mapping()
        member = SimpleNamespace(bot=False, add_roles=AsyncMock(), remove_roles=AsyncMock())
        self.guild.get_member.return_value = member
        payload = SimpleNamespace(guild_id=1, message_id=10, user_id=20, emoji="🎵")

        await self.cog.on_raw_reaction_add(payload)
        await self.cog.on_raw_reaction_remove(payload)

        self.assertEqual(self.guild.get_member.call_args_list, [call(20), call(20)])
        member.add_roles.assert_awaited_once_with(self.role, reason="Role assignment via reaction")
        member.remove_roles.assert_awaited_once_with(self.role, reason="Role removed via reaction")

    async def test_untracked_or_unmapped_reactions_skip_guild_lookup(self):
        await self.configure_mapping()
        fields = dict(guild_id=1, message_id=10, user_id=20, emoji="🎵")
        for override in ({"message_id": 11}, {"emoji": "❌"}, {"guild_id": 2}, {"guild_id": None}):
            with self.subTest(override=override):
                payload = SimpleNamespace(**(fields | override))
                await self.cog.on_raw_reaction_add(payload)
                await self.cog.on_raw_reaction_remove(payload)
        self.bot.get_guild.assert_not_called()

    async def test_bot_reactions_do_not_change_roles(self):
        await self.configure_mapping()
        member = SimpleNamespace(bot=True, add_roles=AsyncMock(), remove_roles=AsyncMock())
        self.guild.get_member.return_value = member
        payload = SimpleNamespace(guild_id=1, message_id=10, user_id=20, emoji="🎵")

        await self.cog.on_raw_reaction_add(payload)
        await self.cog.on_raw_reaction_remove(payload)

        member.add_roles.assert_not_awaited()
        member.remove_roles.assert_not_awaited()
