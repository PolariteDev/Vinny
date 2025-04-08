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
import platform
from discord import app_commands
from discord.ext import commands
import utils.info as info
import utils.db as db
import datetime
import humanfriendly
import importlib
import time

class misc(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@app_commands.command(description="Host information")
	async def host_info(self,interaction: discord.Interaction):
		try:
			embed = discord.Embed(title="Host Information", color=16711680, timestamp=datetime.datetime.now())
			embed.add_field(name="Operating System", value=f"{platform.system()} {platform.release()}")
			embed.add_field(name="", value="")
			embed.add_field(name="Python Version", value=f"{platform.python_version()}")
			embed.add_field(name="Vinny Version", value=f"{info.get_vinny_version()}")
			embed.add_field(name="", value="")
			conn, c = db.db_connect()
			embed.add_field(name="Total moderations", value=f"{db.get_count_of_moderations(c)}")
			conn.close()
			await interaction.response.send_message(embed=embed)
		except Exception as e:
			await interaction.response.send_message(f"Unhandled exception caught:\n```\n{e}\n```", ephemeral=True)

	@app_commands.command(description="Say anything in your current channel")
	@app_commands.describe(message="Message to send")
	@app_commands.describe(channel="Channel to send message in")
	@app_commands.describe(reply_to="Message to reply to (give ID)")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def say(self,interaction: discord.Interaction, message: str, channel: discord.TextChannel = None, reply_to: str = None):
		if channel is not None:
			pass
		else:
			channel = interaction.channel
		
		if reply_to is None:
			await interaction.response.send_message(f"Sent message in {channel.mention}", ephemeral=True)
			await channel.send(message)
		else:
			message_obj = await channel.fetch_message(int(reply_to))
			channel = message_obj.channel
			await interaction.response.send_message(f"Sent reply message in {channel.mention} to {message_obj.jump_url}", ephemeral=True)
			await message_obj.reply(message)

	@app_commands.command(description="View bot uptime")
	async def uptime(self,interaction: discord.Interaction):
		timedelta = datetime.datetime.now(datetime.UTC) - self.bot.start_time
		await interaction.response.send_message(content=f"{humanfriendly.format_timespan(timedelta)}")


	@app_commands.command(description="Get time from host")
	async def host_time(self,interaction: discord.Interaction):
		today = datetime.date.today()
		time_unix_stamp = int(time.time())
		fulldate = time.ctime(time.time())
		now = datetime.datetime.now()
		local_now = now.astimezone()
		local_tz = local_now.tzinfo
		local_tzname = local_tz.tzname(local_now)
		message_content = (
			f"Date: {today} \n"
			f"Time in Unix timestamp (sec. since epoch): {time_unix_stamp}  \n"
			f"{fulldate} \n"
			f"Host timezone (UTC): {local_tzname}"
		)
		await interaction.response.send_message(content=message_content)

	@app_commands.command(description="Time until the Epochalypse of Y2K38")
	async def epochalypse(self,interaction: discord.Interaction):
		time_unix_stamp = int(time.time())
		epochalypsetime = 2147483648
		timeleft = epochalypsetime - time_unix_stamp
		message_content1 = (
			f"Current time in Unix timestamp: {time_unix_stamp} (UTC) <t:{time_unix_stamp}:f>\n"
			f"Epochalypse timestamp: {epochalypsetime} <t:{epochalypsetime}:f> \n"
			f"Seconds left until Epochalypse: **{timeleft}** <t:{epochalypsetime}:R> \n"
			f"Human readable time left until Epochalypse: **{humanfriendly.format_timespan(timeleft)}**"
		)

		await interaction.response.send_message(content=message_content1)
	
async def setup(client):
	importlib.reload(db)
	importlib.reload(info)
	await client.add_cog(misc(client))
