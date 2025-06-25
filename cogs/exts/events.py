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

import discord
from discord.ext import commands
import schedule
import asyncio
from utils import db, utils, embeds
import datetime
import importlib
message_delete_embeds = {} # this is so we can send one message with all the embeds

class events(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def send_pending_delete_events(self):
		for guild_id, embeds in message_delete_embeds.items():
			conn, c = db.db_connect()
			channel_id = db.get_config_value(guild_id, "event_log_channel_id", c, 0)
			conn.close()
			try:
				channel = await self.bot.fetch_channel(channel_id)
			except Exception as e:
				channel = None
				del message_delete_embeds[guild_id]
				return
			# send in batches of 10 embeds so that api doesnt get mad
			for i in range(0, len(embeds), 10):
				batch = embeds[i:i+10]
				try:
					await channel.send(embeds=batch)
				except Exception:
					message_delete_embeds[guild_id] = []
					pass

				# delete the sent embeds from the dictionary and then wait for another schedule job to send & delete the rest
				del message_delete_embeds[guild_id][i:i+10]

	async def scheduler(self):
		while True:
			await asyncio.sleep(1)
			schedule.run_pending()

	async def start_schedule(self):
		schedule.every(10).seconds.do(lambda: asyncio.create_task(events.send_pending_delete_events(self)))

	async def cog_load(self):
		self.start_schedule_task = asyncio.create_task(self.start_schedule())
		self.scheduler_task = asyncio.create_task(self.scheduler())

	async def cog_unload(self):
		if self.scheduler_task:
			self.scheduler_task.cancel()
		if self.start_schedule_task:
			self.start_schedule_task.cancel()

	@commands.Cog.listener()
	async def on_raw_message_delete(self,payload: discord.RawMessageDeleteEvent):
		conn, c = db.db_connect()
		if db.get_config_value(payload.guild_id, "on_message_delete", c) == 0: return conn.close()
		global message_delete_embeds
		if payload.cached_message:
			if db.get_config_value(payload.guild_id, "on_message_delete", c, 1) and payload.cached_message.author.bot: return
			if payload.cached_message.webhook_id: return
			if len(payload.cached_message.content) > 1024: return
		if payload.guild_id not in message_delete_embeds:
			message_delete_embeds[payload.guild_id] = []

		embed = await embeds.delete_message_embed(payload, payload.cached_message)
		message_delete_embeds[payload.guild_id].append(embed)
		conn.close()

	@commands.Cog.listener()
	async def on_message_edit(self,before: discord.Message, after: discord.Message):
		conn, c = db.db_connect()
		if before.author.bot and db.get_config_value(before.guild.id, "bot_filter", c) == 0 or not before.author.bot:
			if db.get_config_value(before.guild.id, "on_message_edit", c) == 0: return conn.close()
			if before.content == after.content: return conn.close()
			channel_id = db.get_config_value(before.guild.id, "event_log_channel_id", c, 0)
			channel = await self.bot.fetch_channel(channel_id)
			embed = await embeds.edit_message_embed(before, after)
			await channel.send(embed=embed)
		conn.close()

	@commands.Cog.listener()
	async def on_raw_message_edit(self,payload: discord.RawMessageUpdateEvent):
		if payload.cached_message is None:
			conn, c = db.db_connect()
			if db.get_config_value(payload.guild_id, "on_message_edit", c) == 0: return conn.close()
			channel_id = db.get_config_value(payload.guild_id, "event_log_channel_id", c, 0)
			conn.close()
			channel = await self.bot.fetch_channel(channel_id)
			event_channel = await self.bot.fetch_channel(payload.channel_id)
			message = await event_channel.fetch_message(payload.message_id)
			if message.webhook_id: return
			embed = await embeds.raw_edit_message_embed(payload=payload, message=message)
			await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_member_update(self,before: discord.Member, after: discord.Member):
		conn, c = db.db_connect()
		if db.get_config_value(before.guild.id, "on_member_update", c) == 0: return conn.close()
		channel_id = db.get_config_value(before.guild.id, "event_log_channel_id", c, 0)
		conn.close()
		channel = await self.bot.fetch_channel(channel_id)
		embed = await embeds.member_update_embed(before, after)
		await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_guild_channel_create(self,event_channel):
		conn, c = db.db_connect()
		if db.get_config_value(event_channel.guild.id, "on_guild_channel_create", c) == 0: return conn.close()
		channel_id = db.get_config_value(event_channel.guild.id, "event_log_channel_id", c, 0)
		conn.close()
		channel = await self.bot.fetch_channel(channel_id)
		embed = await embeds.channel_created(event_channel)
		await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_guild_channel_delete(self,event_channel):
		conn, c = db.db_connect()
		if db.get_config_value(event_channel.guild.id, "on_guild_channel_delete", c) == 0: return conn.close()
		channel_id = db.get_config_value(event_channel.guild.id, "event_log_channel_id", c, 0)
		conn.close()
		channel = await self.bot.fetch_channel(channel_id)
		embed = await embeds.channel_deleted(event_channel)
		await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_member_join(self,member: discord.Member):
		conn, c = db.db_connect()
		if db.get_config_value(member.guild.id, "on_member_join", c) == 0: return conn.close()
		channel = await self.bot.fetch_channel(db.get_config_value(member.guild.id, "event_log_channel_id", c, 0))
		conn.close()
		embed = await embeds.member_join(member)
		await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_member_remove(self,member: discord.Member):
		conn, c = db.db_connect()
		if db.get_config_value(member.guild.id, "on_member_leave", c) == 0: return conn.close()
		channel = await self.bot.fetch_channel(db.get_config_value(member.guild.id, "event_log_channel_id", c, 0))
		conn.close()
		embed = await embeds.member_remove(member)
		await channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_message(self,message: discord.Message):
			if isinstance(message.nonce, str) and not message.nonce.isdigit():
				conn, c = db.db_connect()
				nonce_filtering = db.get_config_value(message.guild.id, "nonce_filter", c)
				if nonce_filtering == 1:
					try:
						channel = await self.bot.fetch_channel(db.get_config_value(message.guild.id, "event_log_channel_id", c, 0))
						await message.delete()
						embed = discord.Embed(title="Hidden nonce message detected", color=16729932, timestamp=datetime.datetime.now())
						embed.add_field(name="Author", value=f"<@{message.author.id}>\n{message.author.id}")
						embed.add_field(name="Channel", value=f"<#{message.channel.id}>\n{message.channel.id}")
						embed.add_field(name="Message ID", value=message.id)
						embed.add_field(name="Message contents", value=f"```\n{message.content}\n```")
						embed.add_field(name="Nonce contents", value=f"```\n{message.nonce}\n```")
						embed.set_thumbnail(url=message.author.avatar)
						await channel.send(embed=embed)
						conn.close()
					except Exception as e:
						print(e)
						conn.close()

	@commands.Cog.listener()
	async def on_guild_remove(self,guild: discord.Guild):
		try:
			conn, c = db.db_connect()
			c.execute('DELETE FROM guilds WHERE guild_id = ?', (guild.id,))
			conn.commit()
			conn.close()
		except Exception:
			pass

async def setup(bot):
	importlib.reload(utils)
	importlib.reload(db)
	importlib.reload(embeds)
	message_delete_embeds = {} # reset to avoid errors
	await bot.add_cog(events(bot))