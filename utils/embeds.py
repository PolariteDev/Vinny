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

# just a bunch of pre-made ready embeds for stuff like logging, etc

import datetime
import discord

from utils import utils

async def delete_message_embed(payload: discord.RawMessageDeleteEvent, message: discord.Message = None):
	embed = discord.Embed(title="Message deleted", color=16729932, timestamp=datetime.datetime.now())
	if payload and not message:
		embed.add_field(name="Author", value=f"*Cannot be retrieved*")
		embed.add_field(name="Channel", value=f"<#{payload.channel_id}>\n{payload.channel_id}")
		embed.add_field(name="Message ID", value=payload.message_id)
		embed.add_field(name="Message contents", value=f"```\nMessage not in internal cache, cannot be retrieved\n```")
	else:
		embed.add_field(name="Author", value=f"<@{message.author.id}>\n{message.author.id}")
		embed.add_field(name="Channel", value=f"<#{message.channel.id}>\n{message.channel.id}")
		embed.add_field(name="Message ID", value=message.id)
		embed.add_field(name="Message contents", value=f"```\n{message.content}\n```")
	return embed

async def edit_message_embed(before: discord.Message = None, after: discord.Message = None, payload: discord.RawMessageUpdateEvent = None):
	embed = discord.Embed(title="Message edited", color=16761035, timestamp=datetime.datetime.now())
	embed.add_field(name="Author", value=f"<@{before.author.id}>\n{before.author.id}")
	embed.add_field(name="Channel", value=f"<#{before.channel.id}>\n{before.channel.id}")
	embed.add_field(name="Message", value=f"{before.jump_url}\n{before.id}")
	embed.add_field(name="Old message contents", value=f"```\n{before.content}\n```")
	embed.add_field(name="New message contents", value=f"```\n{after.content}\n```", inline=True)
	return embed

async def raw_edit_message_embed(payload: discord.RawMessageUpdateEvent, message: discord.Message):
	embed = discord.Embed(title="Message edited", color=16761035, timestamp=datetime.datetime.now())
	embed.add_field(name="Author", value=f"<@{message.author.id}>\n{message.author.id}")
	embed.add_field(name="Channel", value=f"<#{message.channel.id}>\n{message.channel.id}")
	embed.add_field(name="Message", value=f"{message.jump_url}\n{message.id}")
	embed.add_field(name="Old message contents", value=f"```\nMessage not in internal cache, cannot be retrieved\n```")
	embed.add_field(name="New message contents", value=f"```\n{message.content}\n```", inline=True)
	return embed

async def dm_moderation_embed(guild: discord.Guild, victim: discord.User | discord.Member, reason: str, duration: str | None, severity: str, moderation_type: str):
	try:
		if moderation_type == "Ban":
			verb="banned from"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=16711680, timestamp=datetime.datetime.now())
		elif moderation_type == "Mute":
			verb="muted in"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=16744319, timestamp=datetime.datetime.now())
		elif moderation_type == "Warn":
			verb="warned in"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=16572774, timestamp=datetime.datetime.now())
		elif moderation_type == "Kick":
			verb="kicked from"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=16755969, timestamp=datetime.datetime.now())
		elif moderation_type == "Unmute":
			verb="unmuted from"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=7855479, timestamp=datetime.datetime.now())
		elif moderation_type == "Unban":
			verb="unbanned from"
			embed = discord.Embed(title=f"You have been {verb} {guild.name}", color=7855479, timestamp=datetime.datetime.now())
		embed.add_field(name="Reason", value=f"```\n{reason}\n```")
		if severity != "N/A":
			embed.add_field(name="Severity", value=f"{severity}", inline=False)
		if severity == "S2" or severity == "S3":
			embed.add_field(name="Duration", value=f"{duration} (<t:{int((datetime.datetime.now() + utils.parse_duration(duration)).timestamp())}:R>)")
		if guild.icon is not None:
			guild_icon = guild.icon
		else:
			guild_icon = "https://cdn.discordapp.com/embed/avatars/1.png"
		embed.set_thumbnail(url=guild_icon)
		return embed
	except Exception as e:
		print(e)

async def member_update_embed(before: discord.Member, after: discord.Member):
	try:
		if len(after.roles) > len(before.roles):
			role = next(role for role in after.roles if role not in before.roles)
			embed = discord.Embed(title=f"Member Updated - {after.name}", color=65280, timestamp=datetime.datetime.now())
			embed.set_thumbnail(url=after.display_avatar)
			embed.add_field(name="Added role", value=role.mention)
		elif len(after.roles) < len(before.roles):
			role = next(role for role in before.roles if role not in after.roles)
			embed = discord.Embed(title=f"Member Updated - {after.name}", color=16753920, timestamp=datetime.datetime.now())
			embed.set_thumbnail(url=after.display_avatar)
			embed.add_field(name="Removed role", value=role.mention)
		elif before.nick != after.nick:
			embed = discord.Embed(title=f"Member Updated - {after.name}", color=65280, timestamp=datetime.datetime.now())
			embed.set_thumbnail(url=after.display_avatar)
			embed.add_field(name="Old nickname", value=before.nick)
			embed.add_field(name="New nickname", value=after.nick)
		elif before.display_avatar != after.display_avatar:
			embed = discord.Embed(title=f"Member Updated - {after.name}", color=65280, timestamp=datetime.datetime.now())
			embed.set_thumbnail(url=after.display_avatar)
			embed.add_field(name="", value="New display avatar")
		return embed
	except Exception as e:
		print(e)

async def channel_created(channel):
	embed = discord.Embed(title="Channel created", color=8647311, timestamp=datetime.datetime.now())
	embed.add_field(name="Channel", value=f"{channel.mention}\n{channel.id}")
	return embed

async def channel_deleted(channel):
	embed = discord.Embed(title="Channel removed", color=16729932, timestamp=datetime.datetime.now())
	embed.add_field(name="Channel", value=f"`#{channel.name}`\n{channel.id}")
	return embed

async def quickmod_embed(moderator: discord.Member, offending_message: discord.Message):
	embed = discord.Embed(title=f"Quickmod - {offending_message.author.name}", color=16753920)
	embed.add_field(name="Offending message", value=f"{offending_message.jump_url}\n{offending_message.id}\n```\n{offending_message.content}\n```")
	embed.set_thumbnail(url=offending_message.author.avatar)
	embed.set_footer(text="Pick actions below and then afterwards send a message containing moderation reason (type `cancel` to cancel)")
	return embed

async def member_join(member: discord.Member):
	embed = discord.Embed(title=f"Member joined", color=65280, timestamp=datetime.datetime.now())
	embed.add_field(name="User information", value=f"{member.mention}\n{member.name}\n{member.id}")
	embed.add_field(name="Joined at", value=f"<t:{int(member.joined_at.timestamp())}>")
	embed.set_thumbnail(url=member.avatar)
	return embed

async def member_remove(member: discord.Member):
	embed = discord.Embed(title=f"Member left", color=16729932, timestamp=datetime.datetime.now())
	embed.add_field(name="User information", value=f"{member.mention}\n{member.name}\n{member.id}")
	embed.set_thumbnail(url=member.avatar)
	return embed

async def ticket_open(id: int, user: discord.Member, channel: discord.TextChannel, reason: str):
	embed = discord.Embed(title=f"Ticket opened (#{id})", color=0x3452E8, timestamp=datetime.datetime.now())
	embed.add_field(name="Opened By", value=user.mention)
	embed.add_field(name="Channel", value=channel.mention)
	embed.add_field(name="Reason", value=f"{reason}")
	return embed

async def ticket_close(id: int, user: discord.Member, closer: discord.Member, log: str):
	embed = discord.Embed(title=f"Ticket closed (#{id})", color=16729932, timestamp=datetime.datetime.now())
	embed.add_field(name="Opened By", value=user.mention)
	embed.add_field(name="Closed By", value=closer.mention)
	embed.add_field(name="Log", value=log)
	return embed

async def moderation_change_reason(moderator: discord.Member, moderation_id: str, moderation_type: str, new_reason: str, old_reason: str):
	embed = discord.Embed(title=f"Moderation `{moderation_id}` - {moderation_type} (Reason changed)", color=16753920, timestamp=datetime.datetime.now())
	embed.add_field(name="Moderator", value=f"{moderator.mention}")
	embed.add_field(name="Old reason", value=f"`{old_reason}`")
	embed.add_field(name="New reason", value=f"`{new_reason}`")
	embed.set_thumbnail(url=moderator.avatar)
	return embed