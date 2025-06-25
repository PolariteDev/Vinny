# vinny - discord moderation self.bot
# Copyright (C) 2024-2025 Polarograph
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
from discord import app_commands
from discord.ext import commands
import schedule
import asyncio
from utils import db, utils, embeds
import importlib

class unbans(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def start_schedule(self):
		schedule.every().minute.do(lambda: asyncio.create_task(unbans.look_for_unbans(self)))

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def cog_load(self):
		print("starting unban scheduler")
		self.start_schedule_task = asyncio.create_task(self.start_schedule())
		self.scheduler_task = asyncio.create_task(self.scheduler())

	async def cog_unload(self):
		if self.scheduler_task:
			self.scheduler_task.cancel()
		if self.start_schedule_task:
			self.start_schedule_task.cancel()

	async def look_for_unbans(self): # check every active tempban for an unban
		conn, c = db.db_connect()
		unbans = db.get_active_tempbans(conn, c)
		now = datetime.datetime.now()

		try:
			for uban in unbans:
				if uban['unban_time'] <= now:
					conn, c = db.db_connect()
					# if we have a moderation that's past (or equal) to its unban time we will start the unban process
					moderation = db.get_moderation_by_id(uban['moderation_id'], c)

					if moderation:
						guild_id = moderation[1]
						user_id = moderation[2]

						user = await self.bot.fetch_user(int(user_id))
						guild = await self.bot.fetch_guild(int(guild_id))
						try:
							await guild.unban(user, reason="Scheduled unban")
						except Exception:
							pass
						db.set_tempban_inactive(uban['moderation_id'], conn, c)
						print(f"Unbanned {user.name} from {guild.name}")
					conn.close()
		except Exception as e:
			print(f"Error while unbanning: {e}")
		conn.close()

async def setup(bot):
	importlib.reload(db)
	importlib.reload(utils)
	importlib.reload(embeds)
	await bot.add_cog(unbans(bot))