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

import discord
from discord import app_commands
from discord.ext import commands
from utils import db, utils, embeds
from cogs.cmds import moderation
import time
import traceback
import importlib
quick_mod = {}

class quickmod(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.ctx_menu = app_commands.ContextMenu(
			name='Quickmod',
			callback=self.on_quick_mod,
		)
		self.bot.tree.add_command(self.ctx_menu)

	async def on_quick_mod(self,interaction: discord.Interaction, message: discord.Message):
		moderator = interaction.user
		victim = message.author
		if moderator.guild_permissions.moderate_members:
			if victim.guild_permissions.moderate_members:
				return await interaction.response.send_message(content="You cannot moderate other moderators")
			try:
				global quick_mod
				if moderator.id not in quick_mod:
					quick_mod[moderator.id] = {}
				if moderator.guild.id not in quick_mod[moderator.id]:
					quick_mod[moderator.id][moderator.guild.id] = {}
					embed = await embeds.quickmod_embed(moderator, message)
					view = discord.ui.View(timeout=500)
						
					sanction = discord.ui.Select(options=[discord.SelectOption(label="S1", value="S1", default=False),
										discord.SelectOption(label="S2", value="S2", default=True),
										discord.SelectOption(label="S3", value="S3", default=False),
										discord.SelectOption(label="S4", value="S4", default=False)])
					duration = discord.ui.Select(options=[discord.SelectOption(label="1m", value="1m", default=False),
										discord.SelectOption(label="15m", value="15m", default=True),
										discord.SelectOption(label="1h", value="1h", default=False),
										discord.SelectOption(label="10h", value="10h", default=False),
										discord.SelectOption(label="1d", value="1d", default=False),
										discord.SelectOption(label="10d", value="10d", default=False)])
					quick_mod[moderator.id][moderator.guild.id]['sanction'] = "S2"
					quick_mod[moderator.id][moderator.guild.id]['duration'] = "15m"
					async def sanction_callback(interaction: discord.Interaction):
						if interaction.user.id != moderator.id:
							await interaction.response.send_message("You are not the moderator", ephemeral=True)
							return
						quick_mod[moderator.id][moderator.guild.id]['sanction'] = sanction.values[0]
						await interaction.response.defer()
					async def duration_callback(interaction: discord.Interaction):
						if interaction.user.id != moderator.id:
							await interaction.response.send_message("You are not the moderator", ephemeral=True)
							return
						if duration.values[0] == "10d" and sanction.values[0] == "S2":
							duration_new = "7d"
						else:
							duration_new = duration.values[0]
						quick_mod[moderator.id][moderator.guild.id]['duration'] = duration_new
						await interaction.response.defer()
					quick_mod[moderator.id][moderator.guild.id]['message'] = message
					sanction.callback = sanction_callback
					duration.callback = duration_callback
					view.add_item(sanction)
					view.add_item(duration)
					await interaction.response.send_message(content=f"{moderator.mention}", embed=embed, view=view, ephemeral=True)
			except Exception as e:
				print(f"Quickmod error: {traceback.format_exc()}")
		else:
			return await interaction.response.send_message(content="You are not a moderator")

	@commands.Cog.listener()
	async def on_message(self,message: discord.Message):
		try:
			if message.guild.id in quick_mod[message.author.id]:
				await message.delete()
				try:
					if message.content == "cancel":
						del quick_mod[message.author.id][message.guild.id]
						return
					else:
						conn, c = db.db_connect()
						quick_mod_action = quick_mod[message.author.id][message.guild.id]
						if quick_mod_action['sanction'] == "S1":
							moderation_type = "Warn"
							moderation_id = db.insert_moderation(guild_id=message.guild.id, user_id=quick_mod_action['message'].author.id, moderator_id=message.author.id, moderation_type=moderation_type, reason=f"[Quickmod] {message.content}", severity=quick_mod_action['sanction'], time=str(time.time()), duration=None, conn=conn, c=c)
							try:
								channel = await quick_mod_action['message'].author.create_dm()
								await channel.send(embed=await embeds.dm_moderation_embed(guild=message.guild, victim=quick_mod_action['message'].author, reason=f"[Quickmod] {message.content}", duration=None, severity=quick_mod_action['sanction'], moderation_type=moderation_type))
							except Exception:
								pass
							try:
								await moderation.moderation.log_embed(self,victim=quick_mod_action['message'].author, severity=quick_mod_action['sanction'], duration=quick_mod_action['duration'], reason=f"[Quickmod] {message.content}\n\nOffending message:\n```\n{quick_mod_action['message'].content}\n```", moderator=message.author, moderation_id=moderation_id, moderation_type=moderation_type, guild=message.guild)
							except Exception:
								pass
							await message.channel.send(f"Moderation `{moderation_id}`: Warned <@{quick_mod_action['message'].author.id}>: **{quick_mod_action['sanction']}. [Quickmod] {message.content}**")
							del quick_mod[message.author.id][message.guild.id]
							conn.close()
						elif quick_mod_action['sanction'] == "S2":
							moderation_type = "Mute"
							moderation_id = db.insert_moderation(guild_id=message.guild.id, user_id=quick_mod_action['message'].author.id, moderator_id=message.author.id, moderation_type=moderation_type, reason=f"[Quickmod] {message.content}", severity=quick_mod_action['sanction'], time=str(time.time()), duration=quick_mod_action['duration'], conn=conn, c=c)
							duration_delta = utils.parse_duration(quick_mod_action['duration'])
							try:
								channel = await quick_mod_action['message'].author.create_dm()
								await channel.send(embed=await embeds.dm_moderation_embed(guild=message.guild, victim=quick_mod_action['message'].author, reason=f"[Quickmod] {message.content}", duration=quick_mod_action['duration'], severity=quick_mod_action['sanction'], moderation_type=moderation_type))
							except Exception:
								pass
							await quick_mod_action['message'].author.timeout(duration_delta, reason=f"[Quickmod] {message.content} - {message.author.name}")
							try:
								await moderation.moderation.log_embed(self,victim=quick_mod_action['message'].author, severity=quick_mod_action['sanction'], duration=quick_mod_action['duration'], reason=f"[Quickmod] {message.content}\n\nOffending message:\n```\n{quick_mod_action['message'].content}\n```", moderator=message.author, moderation_id=moderation_id, moderation_type=moderation_type, guild=message.guild)
							except Exception:
								pass
							await message.channel.send(f"Moderation `{moderation_id}`: Muted <@{quick_mod_action['message'].author.id}> for **`{quick_mod_action['duration']}`**: **{quick_mod_action['sanction']}. [Quickmod] {message.content}**")
							del quick_mod[message.author.id][message.guild.id]
							conn.close()
						elif quick_mod_action['sanction'] == "S3" or quick_mod_action['sanction'] == "S4":
							moderation_type = "Ban"
							duration = quick_mod_action['duration']
							display_duration = duration
							if quick_mod_action['sanction'] == "S4":
								duration = 'N/A'
								display_duration = "N/A"
							moderation_id = db.insert_moderation(guild_id=message.guild.id, user_id=quick_mod_action['message'].author.id, moderator_id=message.author.id, moderation_type=moderation_type, reason=f"[Quickmod] {message.content}", severity=quick_mod_action['sanction'], time=str(time.time()), duration=duration, conn=conn, c=c)
							try:
								channel = await quick_mod_action['message'].author.create_dm()
								await channel.send(embed=await embeds.dm_moderation_embed(guild=message.guild, victim=quick_mod_action['message'].author, reason=f"[Quickmod] {message.content}", duration=quick_mod_action['duration'], severity=quick_mod_action['sanction'], moderation_type=moderation_type))
							except Exception:
								pass
							await quick_mod_action['message'].author.ban(reason=f"[Quickmod] {message.content} - {message.author.name} banned for {display_duration}")
							try:
								await moderation.moderation.log_embed(self,victim=quick_mod_action['message'].author, severity=quick_mod_action['sanction'], duration=duration, reason=f"[Quickmod] {message.content}\n\nOffending message:\n```\n{quick_mod_action['message'].content}\n```", moderator=message.author, moderation_id=moderation_id, moderation_type=moderation_type, guild=message.guild)
							except Exception:
								pass
							await message.channel.send(f"Moderation `{moderation_id}`: Banned <@{quick_mod_action['message'].author.id}> for **`{display_duration}`**: **{quick_mod_action['sanction']}. [Quickmod] {message.content}**")
							del quick_mod[message.author.id][message.guild.id]
							conn.close()
				except Exception as e:
					print(f"Quickmod error: {traceback.format_exc()}")
		except Exception:
			return

async def setup(bot):
	quick_mod = {}
	importlib.reload(utils)
	importlib.reload(db)
	importlib.reload(embeds)
	importlib.reload(moderation)
	await bot.add_cog(quickmod(bot))