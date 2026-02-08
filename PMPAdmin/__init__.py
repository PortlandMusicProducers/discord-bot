from .PMPAdmin import PMPAdmin
from .ExportMessages import ExportMessages
from .YoutubePlaylistListener import YoutubePlaylistListener
from .ChallengeScraper import ChallengeScraper
from .RoleAssignment import RoleAssignment
from .TalkModerator import TalkModerator

__red_end_user_data_statement__ = (
    "This cog adds admin functions for PMP and other dope stuff."
)

async def setup(bot):
    await bot.add_cog(PMPAdmin(bot))
    await bot.add_cog(ExportMessages(bot))
    await bot.add_cog(YoutubePlaylistListener(bot))
    await bot.add_cog(ChallengeScraper(bot))
    await bot.add_cog(RoleAssignment(bot))
    await bot.add_cog(TalkModerator(bot))