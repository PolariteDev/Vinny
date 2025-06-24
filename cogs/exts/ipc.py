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
#
# NOTE: If you wanna use my dashboard module/IPC extension without complying with above terms,
# then contact me for inquiries/questions for permission. You will only be able to
# use my commits if you have received permission from me. <0vfx@proton.me>

from typing import Dict
import datetime
import discord
from discord import Emoji, app_commands
from discord.ext import commands, ipc
from discord.ext.ipc.server import Server
from discord.ext.ipc.objects import ClientPayload
from utils import utils
import importlib
import asyncio

from utils import db

class Routes(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		if not hasattr(self, "ipc"):
			config_data = utils.load_config()
			self.ipc = ipc.Server(self.bot, secret_key=config_data['dashboard']['ipc_secret'])
	
	async def cog_load(self) -> None:
		asyncio.create_task(self.ipc.start())

	async def cog_unload(self) -> None:
		await self.ipc.stop()
		self.ipc = None

	@Server.route()
	async def get_guild_ids(self, data):
		guild_ids = []
		for guild in self.bot.guilds:
			guild_ids.append(guild.id)
		guild_ids = repr(guild_ids)
		return guild_ids

	@Server.route()
	async def get_guild_name(self, data):
		guild_id = data['guild_id']
		guild = self.bot.get_guild(guild_id)
		return guild.name

	@Server.route()
	async def get_guild_channels(self, data):
		guild_id = data['guild_id']
		guild = self.bot.get_guild(guild_id)
		if guild is not None:
			channels = {channel.id: channel.name for channel in guild.channels if not isinstance(channel, (discord.CategoryChannel, discord.VoiceChannel))}
			return channels
		else:
			return {}

	@Server.route()
	async def get_bot_id(self, data):
		return(str(self.bot.user.id))

	@Server.route()
	async def check_admin(self, data):
		guild_id = data['guild_id']
		user_id = data['user_id']
		guild = self.bot.get_guild(guild_id)
		member = guild.get_member(user_id)
		if member is None:
			return False
		
		if member.guild_permissions.administrator:
			return repr(True)
		else:
			return repr(False)

	@Server.route()
	async def check_mod(self, data):
		guild_id = data['guild_id']
		user_id = data['user_id']
		guild = self.bot.get_guild(guild_id)
		member = guild.get_member(user_id)
		if member is None:
			return False
		
		if member.guild_permissions.administrator:
			return repr(True)

		if member.guild_permissions.moderate_members:
			return repr(True)
		else:
			return repr(False)

	@Server.route()
	async def get_username(self, data):
		try:
			user = self.bot.get_user(data['user_id'])
			if user is None:
				username = (await self.bot.fetch_user(data['user_id'])).name
			else:
				username = user.name
		except Exception:
			pass
		if username is None:
			username = data['id'].id
		return username

	@Server.route()
	async def get_user_avatar_url(self, data):
		avatar_url = None
		try:
			user = self.bot.get_user(data['user_id'])
			if user is None:
				user = await self.bot.fetch_user(data['user_id'])
			avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
		except Exception:
			pass

		if not avatar_url:
			avatar_url = 'https://cdn.discordapp.com/embed/avatars/1.png'

		return avatar_url

	@Server.route()
	async def get_ban_status(self, data):
		try:
			user = await self.bot.fetch_user(data['user_id'])
			guild = self.bot.get_guild(data['guild_id'])
		except Exception as e:
			print(e)
			return repr(False)
		try:
			await guild.fetch_ban(user)
			return repr(True)
		except Exception:
			return repr(False)
		return repr(False)

	@Server.route()
	async def send_appeal_message(self, data):
		try:
			conn, c = db.db_connect()
			config_data = utils.load_config()
			user = await self.bot.fetch_user(data['user_id'])
			guild = self.bot.get_guild(data['guild_id'])
			appeal = data['appeal']
			appeal_id = data['appeal_id']
			embed = discord.Embed(title=f"{user.name}'s appeal - ID {appeal_id}", color=16753920, timestamp=datetime.datetime.now())
			embed.add_field(name="User information", value=f"{user.mention}\n{user.name}\n{user.id}")
			embed.add_field(name="Appeal", value=appeal, inline=False)
			embed.set_footer(text=f"If you'd like to accept this ban appeal, run /accept_appeal appeal:{appeal_id}")
			embed.set_thumbnail(url=user.avatar)
			message = db.get_config_value(guild.id, "appeals_message", c, "New ban appeal")
			appeals_channel_id = db.get_config_value(guild.id, "appeals_channel_id", c, 0)
			poll = discord.Poll("Accept this ban appeal?", duration=datetime.timedelta(days=1.25))
			poll.add_answer(text="Yes")
			poll.add_answer(text="No")
			channel = await self.bot.fetch_channel(appeals_channel_id)
			await channel.send(content=message, embed=embed)
			await asyncio.sleep(0.025)
			await channel.send(poll=poll)
			c.execute("SELECT appeal_id, guild_id, user_id, active, time FROM appeals WHERE guild_id=?", (guild.id,))
			row = c.fetchall()
			if len(row) <= 1:
				await channel.send(content=f"-# Poll automatically created for this appeal\n-# The bot does not use data from this poll, the appeal will have to be accepted by a moderator\n-# If you'd like to disable this feature, you can do so [in the server dashboard]({config_data['dashboard']['url']}/dashboard/server/{guild.id}). This notice will only show up once")
			conn.close()
		except Exception as e:
			print("Encountered error while sending the appeal:", e)

	@app_commands.command(description="View moderations in this server")
	async def server_moderations(self,interaction: discord.Interaction):
		config_data = utils.load_config()
		await interaction.response.send_message(content=f"[Click me!]({config_data['dashboard']['url']}/dashboard/server/{interaction.guild.id}/moderations)")

async def setup(bot):
	importlib.reload(utils)
	await bot.add_cog(Routes(bot))