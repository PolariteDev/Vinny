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
from discord.ui import Button, View, Modal, TextInput
from discord import app_commands, PermissionOverwrite, AllowedMentions, TextStyle
from discord.ext import commands
from discord.ext.commands import Bot
from utils import embeds, utils
import utils.db as db
import importlib

class TicketButton(Button):
	def __init__(self, view_id: str):
		super().__init__(label="Open a Ticket", emoji="📥", style=discord.ButtonStyle.green)
		self.custom_id = view_id

	async def callback(self, interaction: discord.Interaction):
		try:
			conn, c = db.db_connect()
			reason = db.get_ticket_view_reason(interaction.guild.id, self.custom_id, c)
			conn.close()

			if not reason:
				await interaction.response.send_message("This ticket panel is no longer valid.", ephemeral=True) # ?
				return

			await utility.create_ticket(utility, reason, interaction)
		except Exception as e:
			print(f"Error while opening ticket (via panel): {e}")

class TicketView(View):
	def __init__(self, view_id: str, bot: Bot):
		super().__init__(timeout=None)
		self.bot = bot
		self.add_item(TicketButton(view_id))

class TicketPanelModal(Modal, title="Create Ticket Panel"):
	title_input = TextInput(label="Embed Title", style=TextStyle.short, required=True)
	desc_input = TextInput(label="Embed Description", style=TextStyle.paragraph, required=True)
	reason_input = TextInput(label="Ticket Reason", style=TextStyle.short, required=True)

	async def on_submit(self, interaction: discord.Interaction):
		title = self.title_input.value
		description = self.desc_input.value
		reason = self.reason_input.value

		embed = discord.Embed(title=title, description=description, color=0x00863A)
		embed.set_footer(text="Vinny Tickets", icon_url=interaction.client.user.display_avatar.url)
		embed.timestamp = datetime.now()

		channel = interaction.channel

		msg = await channel.send(embed=embed, view=TicketView("temp", interaction.client))

		await interaction.response.send_message(f"Ticket panel created sucessfully: {msg.jump_url}", ephemeral=True)

		view_id = f"{interaction.guild.id}:{msg.id}"

		conn, c = db.db_connect()
		db.insert_ticket_view(interaction.guild.id, msg.id, view_id, reason, conn, c)
		conn.close()

		view = TicketView(view_id, interaction.client)
		await msg.edit(view=view)

class utility(commands.Cog):
	def __init__(self, bot: Bot) -> None:
		self.bot = bot

	async def create_ticket(self, reason: str, interaction: discord.Interaction):
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

			tickets_category_id = db.get_config_value(guild.id, "tickets_category_id", c, 0)

			if tickets_category_id != 0:
				tickets_category = discord.utils.get(guild.categories, id=tickets_category_id)
				channel = await guild.create_text_channel(name=f"ticket-{ticket_id}", overwrites=overwrites, reason=f"Ticket #{ticket_id} opened by {user} for: {reason}", category=tickets_category)
			else:
				channel = await guild.create_text_channel(name=f"ticket-{ticket_id}", overwrites=overwrites, reason=f"Ticket #{ticket_id} opened by {user} for: {reason}")

			conn, c = db.db_connect()

			db.update_ticket_channel_id(guild.id, ticket_id, channel.id, conn, c) # we now put in the channel ID since it exists

			log_channel_id = db.get_config_value(guild.id, "log_channel_id", c, 0)

			conn.close()

			# and now, we notify everyone available
			embed = discord.Embed(title="New Ticket Opened", color=0x3452E8, timestamp=datetime.now())
			embed.add_field(name="By", value=user.mention)
			embed.add_field(name="Reason", value=f"{reason}")
			embed.set_footer(text="To close this ticket, use the /close_ticket command", icon_url=interaction.client.user.display_avatar.url)
			await channel.send(content="@everyone", embed=embed, allowed_mentions=AllowedMentions(everyone=True))
			await interaction.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)

			# log the ticket creation
			embed = await embeds.open_ticket(ticket_id, user, channel, reason)
			try:
				log_channel = await self.bot.fetch_channel(log_channel_id)
				await log_channel.send(embed=embed)
			except Exception as e:
				pass
		except Exception as e:
			print(f"Error while opening ticket: {e}")
			await interaction.response.send_message("An error occurred while opening your ticket.", ephemeral=True)

	@app_commands.command(description="Open a ticket to server staff")
	@app_commands.describe(reason="Ticket reason")
	async def ticket(self, interaction: discord.Interaction, reason: str):
		conn, c = db.db_connect()
		tickets = db.get_config_value(interaction.guild.id, "tickets", c, False)
		conn.close()
		if tickets:
			await self.create_ticket(reason=reason, interaction=interaction) # abstracted
		else:
			await interaction.response.send_message("This server does not have the /ticket command enabled.", ephemeral=True)

	@app_commands.command(description="Close the current ticket")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def close_ticket(self, interaction: discord.Interaction):
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
			embed = await embeds.close_ticket(ticket_id, user, closer, ticket_url)
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

	@app_commands.command(description="Create a ticket panel with a button")
	@app_commands.checks.has_permissions(manage_guild=True)
	async def ticket_panel(self, interaction: discord.Interaction):
		await interaction.response.send_modal(TicketPanelModal())

async def setup(bot):
	importlib.reload(db)
	importlib.reload(utils)
	importlib.reload(embeds)
	await bot.add_cog(utility(bot))