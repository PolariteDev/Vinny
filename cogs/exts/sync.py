# save anything to this file to trigger a sync, recommended after every update (eg: printf "\n" >> sync.py)
from discord.ext import commands

class sync(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		synced = await self.bot.tree.sync()
		print(f"synced {len(synced)} commands")

	async def cog_load(self):
		if self.bot.is_ready():
			synced = await self.bot.tree.sync()
			print(f"synced {len(synced)} commands")

async def setup(client):
	await client.add_cog(sync(client))