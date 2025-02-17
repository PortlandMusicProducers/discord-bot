from .PMPAdmin import PMPAdmin

__red_end_user_data_statement__ = (
    "This cog adds admin functions for PMP"
)

async def setup(bot):
    await bot.add_cog(PMPAdmin(bot))