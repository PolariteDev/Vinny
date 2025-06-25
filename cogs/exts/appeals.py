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
import sqlite3
import time
import discord
from discord import app_commands
from discord.ext import commands
import schedule
import asyncio
from dashboard.dashboard import appeal
from utils import db, utils, embeds
import importlib
from cogs.cmds import moderation

class appeals(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.conn, self.c = db.db_connect()

	async def cog_unload(self):
		self.conn.close()

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def start_schedule(self):
		schedule.every().minute.do(lambda: asyncio.create_task(self.update_appeal_cooldowns()))

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def cog_load(self):
		print("starting appeal scheduler")
		self.start_schedule_task = asyncio.create_task(self.start_schedule())
		self.scheduler_task = asyncio.create_task(self.scheduler())

	async def cog_unload(self):
		if self.scheduler_task:
			self.scheduler_task.cancel()
		if self.start_schedule_task:
			self.start_schedule_task.cancel()

	def get_active_cooldown_appeals(self, c: sqlite3.Cursor):
		c.execute("SELECT guild_id, user_id, active, time FROM appeals WHERE cooldown=true")
		results = []
		for row in c.fetchall():
			guild_id = row[0]
			user_id = row[1]
			time_unix = float(row[3])
			time_obj = datetime.datetime.fromtimestamp(time_unix)
			updated_time = time_obj + datetime.timedelta(days=30)
			results.append({
				'guild_id': guild_id,
				'user_id': user_id,
				'appeal_time': updated_time
			})
		return results

	async def update_appeal_cooldowns(self):
		conn, c = self.conn, self.c
		appeals = self.get_active_cooldown_appeals(c)
		now = datetime.datetime.now()

		try:
			for appeal in appeals:
				if appeal['appeal_time'] <= now:
					conn, c = db.db_connect()

					guild_id = appeal['guild_id']
					user_id = appeal['user_id']

					user = await self.bot.fetch_user(int(user_id))
					guild = await self.bot.fetch_guild(int(guild_id))
					c.execute('UPDATE appeals SET cooldown=false WHERE guild_id=? AND user_id=?', (guild_id, user_id,))
					conn.commit()
					print(f"Appeal cooldown for {user.name} ended from {guild.name}")
		except Exception as e:
			print(f"Error while updating appeal cooldown: {e}")

	@app_commands.command(description="Accept an appeal")
	@app_commands.describe(appeal="Appeal to accept (provide ID)")
	@app_commands.describe(reason_old="Reason of unban")
	@app_commands.rename(reason_old="reason")
	async def accept_appeal(self,interaction: discord.Interaction, appeal: int, reason_old: str = "Unbanned via appeal"):
		conn, c = db.db_connect()
		c.execute("SELECT appeal_id, guild_id, user_id, active, time FROM appeals WHERE active=true AND appeal_id=?", (appeal,))
		row = c.fetchall()
		if row == []:
			return await interaction.response.send_message(f"Invalid appeal ID", ephemeral=True)
		record = row[0]
		victim = await self.bot.fetch_user(record[2])
		success, message = utils.permission_check(interaction.user, victim, "Ban")
		reason = f"[Appeal - {record[0]}] " + reason_old
		if success:
			try:
				guild_id = interaction.guild.id
				user_id = victim.id
				moderator_id = interaction.user.id
				try:
					await interaction.guild.fetch_ban(victim)
				except Exception:
					return await interaction.response.send_message(f"This user isn't banned", ephemeral=True)
				moderation_id = db.insert_moderation(guild_id=guild_id, user_id=user_id, moderator_id=moderator_id, moderation_type="Unban", reason=reason, severity="N/A", duration=None, time=str(time.time()), conn=conn, c=c)
				conn.close()
				await interaction.response.send_message(f"Moderation `{moderation_id}`: Unbanned <@{user_id}>: **{reason}**")
				await interaction.guild.unban(user=victim, reason=f"{reason} - Unbanned by {interaction.user.name}")
				try:
					channel = await victim.create_dm()
					await channel.send(embed=await embeds.dm_moderation_embed(guild=interaction.guild, victim=victim, reason=reason, duration=None, severity="N/A", moderation_type="Unban"))
				except Exception:
					pass
				await moderation.moderation.log_embed(self,victim=victim, severity="N/A", duration=None, reason=reason_old, moderator=interaction.user, moderation_id=moderation_id, moderation_type=f"Unban (via Appeal - {record[0]})", guild=interaction.guild)
			except Exception as e:
				await interaction.response.send_message(f"Unhandled exception caught:\n```\n{e}\n```", ephemeral=True)
		else:
			await interaction.response.send_message(message, ephemeral=True)

async def setup(bot):
	importlib.reload(db)
	importlib.reload(utils)
	importlib.reload(embeds)
	await bot.add_cog(appeals(bot))