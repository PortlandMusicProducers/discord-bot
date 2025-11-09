import os
import sqlite3
import discord
from redbot.core import commands

class RoleAssignment(commands.Cog):
    """Simple role-assignment cog using emoji reactions and a small sqlite DB."""

    def __init__(self, bot):
        self.bot = bot
        # DB lives in data/ under repo root (created if missing)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        data_dir = os.path.join(base, "data")
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.path.join(data_dir, "roleassign.sqlite")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # In-memory cache for quick membership checks:
        # { guild_id: { message_id: category, ... }, ... }
        self.cache = {}
        # Also keep a flat set for ultra-fast "is this message tracked?"
        self.tracked_messages = set()

        # Emoji->role mapping cache:
        # { guild_id: { message_id: { emoji_str: role_id, ... }, ... }, ... }
        self.emoji_map = {}
        self._load_cache()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS role_messages (
                guild_id TEXT NOT NULL,
                category TEXT NOT NULL,
                message_id TEXT NOT NULL,
                PRIMARY KEY (guild_id, category)
            )
            """
        )

        # new table for emoji->role mappings
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS emoji_role_map (
                guild_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                emoji TEXT NOT NULL,
                role_id TEXT NOT NULL,
                PRIMARY KEY (guild_id, message_id, emoji)
            )
            """
        )
        self.conn.commit()

    def _load_cache(self):
        """Load DB into memory and populate tracked_messages set and emoji_map."""
        cur = self.conn.execute("SELECT guild_id, category, message_id FROM role_messages")
        rows = cur.fetchall()
        self.cache = {}
        self.tracked_messages.clear()
        for r in rows:
            gid = str(r["guild_id"])
            mid = str(r["message_id"])
            cat = str(r["category"])
            self.cache.setdefault(gid, {})[mid] = cat
            self.tracked_messages.add(mid)

        # load emoji->role mappings
        cur2 = self.conn.execute("SELECT guild_id, message_id, emoji, role_id FROM emoji_role_map")
        rows2 = cur2.fetchall()
        self.emoji_map = {}
        for r in rows2:
            gid = str(r["guild_id"])
            mid = str(r["message_id"])
            emo = str(r["emoji"])
            rid = str(r["role_id"])
            self.emoji_map.setdefault(gid, {}).setdefault(mid, {})[emo] = rid

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def roleassign(self, ctx, category: str = None, message_id: str = None):
        """
        Configure role-assign message:
        - No args: list current mappings for this guild
        - Usage: roleassign <category> <message_id>
        - Special: roleassign remove <category>  -> deletes that category mapping
        Example categories: daw, genre
        """
        guild_id = str(ctx.guild.id)

        # Delete mapping: roleassign remove <category>
        if category and category.lower() in ("remove", "delete") and message_id:
            cat_to_delete = message_id.lower()
            self.conn.execute("DELETE FROM role_messages WHERE guild_id = ? AND category = ?", (guild_id, cat_to_delete))
            self.conn.commit()
            # refresh caches
            self._load_cache()
            return await ctx.send(f"Removed role-assign mapping for category '{cat_to_delete}'")

        # List current mappings when no args
        if category is None:
            rows = self.conn.execute(
                "SELECT category, message_id FROM role_messages WHERE guild_id = ?", (guild_id,)
            ).fetchall()
            if not rows:
                await ctx.send("No role assignment messages configured for this guild.")
                return
            lines = [f"{r['category']}: {r['message_id']}" for r in rows]
            await ctx.send("Current role-assign messages:\n" + "\n".join(lines))
            return

        if message_id is None:
            await ctx.send("Usage: roleassign <category> <message_id>  (or 'roleassign remove <category>')")
            return

        category = category.lower()
        self.conn.execute(
            "INSERT OR REPLACE INTO role_messages (guild_id, category, message_id) VALUES (?, ?, ?)",
            (guild_id, category, str(message_id)),
        )
        self.conn.commit()

        # refresh caches for this guild
        self._load_cache()
        await ctx.send(f"Role-assign message for '{category}' set to {message_id}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def rolemap(self, ctx, action: str = None, category: str = None, emoji: str = None, role: discord.Role = None):
        """
        Manage emoji -> role mappings.
        Usage:
          rolemap add <category> <emoji> <@role>
          rolemap remove <category> <emoji>
          rolemap list [<category>]
        The emoji should be pasted exactly as you would react with it.
        """
        guild_id = str(ctx.guild.id)
        if action is None:
            return await ctx.send("Usage: rolemap add|remove|list ...")

        action = action.lower()
        if action == "list":
            if category:
                # find message for category
                row = self.conn.execute("SELECT message_id FROM role_messages WHERE guild_id = ? AND category = ?", (guild_id, category.lower())).fetchone()
                if not row:
                    return await ctx.send(f"No role-assign message configured for category '{category}'.")
                message_id = str(row["message_id"])
                mappings = self.emoji_map.get(guild_id, {}).get(message_id, {})
                if not mappings:
                    return await ctx.send("No emoji mappings for that message.")
                lines = []
                for emo, rid in mappings.items():
                    r = ctx.guild.get_role(int(rid)) if rid.isdigit() else None
                    lines.append(f"{emo} -> {r.mention if r else rid}")
                await ctx.send("Mappings:\n" + "\n".join(lines))
            else:
                # list all categories and counts
                rows = self.conn.execute("SELECT category, message_id FROM role_messages WHERE guild_id = ?", (guild_id,)).fetchall()
                if not rows:
                    return await ctx.send("No role-assign messages configured.")
                lines = []
                for r in rows:
                    mid = str(r["message_id"])
                    cat = str(r["category"])
                    count = len(self.emoji_map.get(guild_id, {}).get(mid, {}))
                    lines.append(f"{cat}: {mid} ({count} mappings)")
                await ctx.send("\n".join(lines))
            return

        if action == "add":
            if not category or not emoji or not role:
                return await ctx.send("Usage: rolemap add <category> <emoji> <@role>")
            # get message id for category
            row = self.conn.execute("SELECT message_id FROM role_messages WHERE guild_id = ? AND category = ?", (guild_id, category.lower())).fetchone()
            if not row:
                return await ctx.send("No role-assign message for that category. Set it with roleassign first.")
            message_id = str(row["message_id"])
            emoji_key = emoji  # store emoji exactly as provided (should match str(payload.emoji))
            self.conn.execute(
                "INSERT OR REPLACE INTO emoji_role_map (guild_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?)",
                (guild_id, message_id, emoji_key, str(role.id)),
            )
            self.conn.commit()
            # update in-memory map
            self.emoji_map.setdefault(guild_id, {}).setdefault(message_id, {})[emoji_key] = str(role.id)
            await ctx.send(f"Mapped {emoji} -> {role.mention} for category {category}")
            return

        if action == "remove":
            if not category or not emoji:
                return await ctx.send("Usage: rolemap remove <category> <emoji>")
            row = self.conn.execute("SELECT message_id FROM role_messages WHERE guild_id = ? AND category = ?", (guild_id, category.lower())).fetchone()
            if not row:
                return await ctx.send("No role-assign message for that category.")
            message_id = str(row["message_id"])
            emoji_key = emoji
            self.conn.execute("DELETE FROM emoji_role_map WHERE guild_id = ? AND message_id = ? AND emoji = ?", (guild_id, message_id, emoji_key))
            self.conn.commit()
            # update cache
            self.emoji_map.get(guild_id, {}).get(message_id, {}).pop(emoji_key, None)
            await ctx.send(f"Removed mapping for {emoji} in category {category}")
            return

        await ctx.send("Unknown action. Use add|remove|list.")
        return

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def rolepopulate(self, ctx, category: str = None):
        """
        Populate tracked role-assignment messages with all mapped emojis.
        Usage:
          rolepopulate            -> populate all configured messages in this guild
          rolepopulate <category> -> populate only the message for that category
        The command will attempt to find the message by ID across text channels,
        then add each mapped emoji as a reaction.
        """
        guild = ctx.guild
        gid = str(guild.id)

        # gather target message IDs
        if category:
            row = self.conn.execute(
                "SELECT message_id FROM role_messages WHERE guild_id = ? AND category = ?",
                (gid, category.lower()),
            ).fetchone()
            if not row:
                return await ctx.send(f"No role-assign message configured for category '{category}'.")
            targets = [str(row["message_id"])]
        else:
            rows = self.conn.execute(
                "SELECT message_id FROM role_messages WHERE guild_id = ?", (gid,)
            ).fetchall()
            if not rows:
                return await ctx.send("No role-assign messages configured for this guild.")
            targets = [str(r["message_id"]) for r in rows]

        await ctx.send(f"Populating {len(targets)} message(s) with mapped emojis...")

        populated = 0
        errors = []

        for mid in targets:
            mappings = self.emoji_map.get(gid, {}).get(mid, {})
            if not mappings:
                # nothing to add for this message
                continue

            message_obj = None
            # find message by searching text channels (fetch_message requires channel)
            for ch in guild.text_channels:
                try:
                    message_obj = await ch.fetch_message(int(mid))
                    break
                except (discord.NotFound, discord.Forbidden):
                    continue
                except Exception:
                    # other HTTP errors - skip this channel
                    continue

            if not message_obj:
                errors.append(f"Message {mid} not found in any accessible text channel.")
                continue

            # add each emoji as a reaction
            for emo in mappings.keys():
                try:
                    # parse custom emoji strings into PartialEmoji if necessary
                    react = None
                    if isinstance(emo, str) and emo.startswith("<") and ":" in emo:
                        try:
                            react = discord.PartialEmoji.from_str(emo)
                        except Exception:
                            react = emo
                    else:
                        react = emo
                    await message_obj.add_reaction(react)
                except Exception as e:
                    # keep going, but record error
                    errors.append(f"Failed to add {emo} to message {mid}: {e}")

            populated += 1

        reply_lines = [f"Populated {populated} message(s)."]
        if errors:
            reply_lines.append("Some errors occurred:")
            reply_lines.extend(errors[:10])
            if len(errors) > 10:
                reply_lines.append(f"...and {len(errors)-10} more errors")
        await ctx.send("\n".join(reply_lines))

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def rolemigrate(self, ctx, source: str, dest: str):
        """
        Move emoji->role mappings from source -> dest.
        source/dest may be a message ID or a category name (category will be looked up).
        Usage:
          rolemigrate <source_msg_or_category> <dest_msg_or_category>
        """
        guild_id = str(ctx.guild.id)

        def resolve(arg: str):
            # if numeric assume message id, otherwise treat as category and look up its message_id
            if arg.isdigit():
                return arg
            row = self.conn.execute("SELECT message_id FROM role_messages WHERE guild_id = ? AND category = ?", (guild_id, arg.lower())).fetchone()
            return str(row["message_id"]) if row else None

        src_mid = resolve(source)
        dst_mid = resolve(dest)
        if not src_mid:
            return await ctx.send(f"Source '{source}' not found (not a message id and no category).")
        if not dst_mid:
            return await ctx.send(f"Destination '{dest}' not found (not a message id and no category).")

        # copy rows from src to dst (skip duplicates)
        rows = self.conn.execute("SELECT emoji, role_id FROM emoji_role_map WHERE guild_id = ? AND message_id = ?", (guild_id, src_mid)).fetchall()
        if not rows:
            return await ctx.send("No mappings found for source message.")
        inserted = 0
        for r in rows:
            emo = str(r["emoji"])
            rid = str(r["role_id"])
            # insert or replace for destination
            self.conn.execute("INSERT OR REPLACE INTO emoji_role_map (guild_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?)", (guild_id, dst_mid, emo, rid))
            inserted += 1
        self.conn.commit()
        # reload cache
        self._load_cache()
        await ctx.send(f"Migrated {inserted} mapping(s) from {src_mid} to {dst_mid}.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # fast-filter: skip if message_id not tracked
        if payload.message_id is None or str(payload.message_id) not in self.tracked_messages:
            return
        # ignore bots and DMs
        if payload.user_id is None or payload.guild_id is None:
            return
        if payload.user_id == self.bot.user.id:
            return

        gid = str(payload.guild_id)
        mid = str(payload.message_id)
        emoji_key = str(payload.emoji)

        role_id = self.emoji_map.get(gid, {}).get(mid, {}).get(emoji_key)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # resolve role
        target_role = guild.get_role(int(role_id)) if role_id.isdigit() else next((r for r in guild.roles if r.name == role_id), None)
        if target_role:
            try:
                await member.add_roles(target_role, reason="Role assignment via reaction")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.message_id is None or str(payload.message_id) not in self.tracked_messages:
            return
        if payload.user_id is None or payload.guild_id is None:
            return

        gid = str(payload.guild_id)
        mid = str(payload.message_id)
        emoji_key = str(payload.emoji)
        role_id = self.emoji_map.get(gid, {}).get(mid, {}).get(emoji_key)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        target_role = guild.get_role(int(role_id)) if role_id.isdigit() else next((r for r in guild.roles if r.name == role_id), None)
        if target_role:
            try:
                await member.remove_roles(target_role, reason="Role removed via reaction")
            except Exception:
                pass

    def cog_unload(self):
        try:
            self.conn.close()
        except Exception:
            pass

def setup(bot):
    bot.add_cog(RoleAssignment(bot))