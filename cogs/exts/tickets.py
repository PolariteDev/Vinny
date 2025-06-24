# vinny - discord moderation bot
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

import time
from discord.ext import commands
import asyncio
import schedule
import importlib
from utils import db

class tickets(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def start_schedule(self):
		schedule.every().minute.do(lambda: asyncio.create_task(self.cleanup_old_tickets()))

	async def cog_load(self):
		print("starting ticket scheduler")
		self.start_schedule_task = asyncio.create_task(self.start_schedule())
		self.scheduler_task = asyncio.create_task(self.scheduler())

	async def cog_unload(self):
		if self.scheduler_task:
			self.scheduler_task.cancel()
		if self.start_schedule_task:
			self.start_schedule_task.cancel()

	async def cleanup_old_tickets(self):
		current_time = time.time()
		thirty_days_ago = current_time - (30 * 24 * 60 * 60)
		conn, c = db.db_connect()
		try:
			c.execute("SELECT guild_id, ticket_id, channel_id, active FROM tickets WHERE (active = 1 OR (active = 0 AND messages != 'deleted')) AND CAST(time AS REAL) <= ?", (thirty_days_ago,))
			tickets_to_clean = c.fetchall()
			for ticket in tickets_to_clean:
				guild_id, ticket_id, channel_id, active = ticket
				if active:
					try:
						guild = self.bot.get_guild(guild_id)
						if guild and channel_id:
							channel = guild.get_channel(channel_id)
							if channel:
								await channel.delete(reason=f"Ticket #{ticket_id} auto-closed after 30 days")
					except Exception:
						pass
				c.execute("UPDATE tickets SET active=0, closer_id=0, messages='deleted' WHERE guild_id=? AND ticket_id=?", (guild_id, ticket_id))
			conn.commit()
		except Exception:
			pass
		finally:
			conn.close()

async def setup(bot):
	importlib.reload(db)
	await bot.add_cog(tickets(bot))