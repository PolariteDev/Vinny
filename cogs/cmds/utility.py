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

from datetime import datetime
import json
from time import time
import discord
from discord import app_commands, PermissionOverwrite, AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot
from utils import embeds, utils
import utils.db as db
import importlib

class utility(commands.Cog):
	def __init__(self, bot: Bot) -> None:
		self.bot = bot

	@app_commands.command(description="Open a ticket to server staff")
	@app_commands.describe(reason="Ticket reason")
	async def ticket(self, interaction: discord.Interaction, reason: str):
		try:
			guild = interaction.guild
			user = interaction.user

			conn, c = db.db_connect()

			ticket_id = db.insert_ticket(guild.id, user.id, reason, str(int(time())), conn, c) # create the ticket in our database

			mod_roles = [role for role in guild.roles if role.permissions.moderate_members] # collect all roles that have the moderate_members permission

			# start with @everyone denied & the ticket creator allowed
			overwrites = {
				guild.default_role: PermissionOverwrite(read_messages=False),
				user: PermissionOverwrite(read_messages=True, send_messages=True),
			}

			# let the mod roles we collected earlier view & send messages to the channel
			for role in mod_roles:
				overwrites[role] = PermissionOverwrite(read_messages=True, send_messages=True)

			channel = await guild.create_text_channel(name=f"ticket-{ticket_id}", overwrites=overwrites, reason=f"Ticket #{ticket_id} opened by {user} for: {reason}")

			conn, c = db.db_connect()

			db.update_ticket_channel_id(guild.id, ticket_id, channel.id, conn, c) # we now put in the channel ID since it exists

			log_channel_id = db.get_config_value(guild.id, "log_channel_id", c, 0)

			conn.close()

			# and now, we notify everyone available
			embed = discord.Embed(title="New Ticket Opened", color=0x3452E8, timestamp=datetime.now())
			embed.add_field(name="By", value=user.mention)
			embed.add_field(name="Reason", value=f"{reason}")
			await channel.send(content="@everyone", embed=embed, allowed_mentions=AllowedMentions(everyone=True))
			await interaction.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)

			# log the ticket creation
			embed = await embeds.ticket_open(ticket_id, user, channel, reason)
			try:
				log_channel = await self.bot.fetch_channel(log_channel_id)
				await log_channel.send(embed=embed)
			except Exception as e:
				pass
		except Exception as e:
			print(f"Error while opening ticket: {e}")
			await interaction.response.send_message("An error occurred while opening your ticket.", ephemeral=True)

	@app_commands.command(description="Close the current ticket")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def ticket_close(self, interaction: discord.Interaction):
		try:
			guild = interaction.guild
			channel = interaction.channel
			closer = interaction.user

			conn, c = db.db_connect()
			c.execute("SELECT ticket_id, user_id FROM tickets WHERE guild_id = ? AND channel_id = ? AND active = 1", (guild.id, channel.id))
			row = c.fetchone()
			if not row:
				conn.close()
				await interaction.response.send_message("This channel is not an active ticket.", ephemeral=True)
				return
			ticket_id, user_id = row

			db.close_ticket(guild.id, ticket_id, closer.id, conn, c) # mark inactive & save the closer

			log_channel_id = db.get_config_value(guild.id, "log_channel_id", c, 0)

			conn.close()

			# finally just reply to the closer & delete the ticket channel
			await interaction.response.send_message(f"Ticket #{ticket_id} closed", ephemeral=True)
			await channel.delete(reason=f"Ticket #{ticket_id} closed by {closer}")

			user = self.bot.get_user(user_id)

			config_data = utils.load_config()
			ticket_url = f"[Click me!]({config_data['dashboard']['url']}/dashboard/server/{interaction.guild.id}/ticket/{ticket_id})"

			# log the ticket closure, with the ticket log available on web
			embed = await embeds.ticket_close(ticket_id, user, closer, ticket_url)
			try:
				log_channel = await self.bot.fetch_channel(log_channel_id)
				await log_channel.send(embed=embed)
			except Exception as e:
				pass
		except Exception as e:
			print(f"Error while closing ticket: {e}")
			await interaction.response.send_message("An error occurred while closing this ticket.", ephemeral=True)

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		# ignore bots & DMs
		if message.author.bot or not message.guild:
			return

		channel = message.channel
		guild = message.guild

		conn, c = db.db_connect()
		# we look for an active ticket with this channel_id
		c.execute('SELECT ticket_id, messages FROM tickets WHERE guild_id = ? AND channel_id = ? AND active = 1', (guild.id, channel.id))
		row = c.fetchone()
		if not row:
			conn.close()
			return

		ticket_id, messages_json = row
		try:
			msgs = json.loads(messages_json) if messages_json else []
		except json.JSONDecodeError:
			msgs = []

		# append the new message
		msgs.append({
			"message_id": message.id,
			"author_id": message.author.id,
			"content": message.content,
			"timestamp": int(time())
		})

		# now, we update the messages in the db
		updated = json.dumps(msgs)
		c.execute('UPDATE tickets SET messages = ? WHERE guild_id = ? AND ticket_id = ?', (updated, guild.id, ticket_id))
		conn.commit()
		conn.close()

	@commands.Cog.listener()
	async def on_message_edit(self, before: discord.Message, after: discord.Message):
		# ignore bots & DMs
		if before.author.bot or not before.guild:
			return

		conn, c = db.db_connect()
		# we look for an active ticket with this channel_id
		c.execute('SELECT ticket_id, messages FROM tickets WHERE guild_id = ? AND channel_id = ? AND active = 1', (before.guild.id, before.channel.id))
		row = c.fetchone()
		if not row:
			conn.close()
			return

		ticket_id, messages_json = row
		try:
			msgs = json.loads(messages_json) if messages_json else []
		except json.JSONDecodeError:
			msgs = []

		# look for the old message & add the edit
		for msg in msgs:
			if msg.get("message_id") == before.id:
				edits = msg.setdefault("edits", {})
				edit_num = str(len(edits))
				edits[edit_num] = {
					"new": after.content,
					"timestamp": int(time())
				}
				break

		# now, we update the messages in the db
		updated = json.dumps(msgs)
		c.execute('UPDATE tickets SET messages = ? WHERE guild_id = ? AND ticket_id = ?', (updated, before.guild.id, ticket_id))
		conn.commit()
		conn.close()

	@commands.Cog.listener()
	async def on_message_delete(self, message: discord.Message):
		# ignore bots & DMs
		if message.author.bot or not message.guild:
			return

		conn, c = db.db_connect()
		# we look for an active ticket with this channel_id
		c.execute('SELECT ticket_id, messages FROM tickets WHERE guild_id = ? AND channel_id = ? AND active = 1', (message.guild.id, message.channel.id))
		row = c.fetchone()
		if not row:
			conn.close()
			return

		ticket_id, messages_json = row
		try:
			msgs = json.loads(messages_json) if messages_json else []
		except json.JSONDecodeError:
			msgs = []

		# look for the old message & mark it as deleted
		for msg in msgs:
			if msg.get("message_id") == message.id:
				msg["deleted"] = True
				break

		# now, we update the messages in the db
		updated = json.dumps(msgs)
		c.execute('UPDATE tickets SET messages = ? WHERE guild_id = ? AND ticket_id = ?', (updated, message.guild.id, ticket_id))
		conn.commit()
		conn.close()

async def setup(bot):
	importlib.reload(db)
	importlib.reload(utils)
	importlib.reload(embeds)
	await bot.add_cog(utility(bot))