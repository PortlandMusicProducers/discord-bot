from .PMPAdmin import PMPAdmin
from .ExportMessages import ExportMessages
from .YoutubePlaylistListener import YoutubePlaylistListener
from .ChallengeScraper import ChallengeScraper
from .RoleAssignment import RoleAssignment
from .TalkModerator import TalkModerator
from .SupabaseMemberSync import SupabaseMemberSync

__red_end_user_data_statement__ = (
    "When Supabase sync is configured, this cog mirrors PMP member IDs and their "
    "assigned role IDs and names to the configured Supabase project."
)

async def setup(bot):
    await bot.add_cog(PMPAdmin(bot))
    await bot.add_cog(ExportMessages(bot))
    await bot.add_cog(YoutubePlaylistListener(bot))
    await bot.add_cog(ChallengeScraper(bot))
    await bot.add_cog(RoleAssignment(bot))
    await bot.add_cog(TalkModerator(bot))
    await bot.add_cog(SupabaseMemberSync(bot))
