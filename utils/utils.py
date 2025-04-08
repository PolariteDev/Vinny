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

import re
import datetime
import discord
import sys
from typing import Union

if sys.version_info >= (3, 11): # compat with older python (you'll need to install tomli from pip though)
	import tomllib
else:
	import tomli as tomllib

def parse_duration(duration_str): # convert 1m, 1h, 1d, etc to seconds and then to a timedelta
	pattern = r"(\d+)([mhd]?)"
	match = re.search(pattern, duration_str)
	if match:
		num, unit = match.groups()
		if unit == 'm':
			factor = 60
		elif unit == 'h':
			factor = 3600
		elif unit == 'd':
			factor = 86400
		else:
			factor = 1
		
		total_seconds = float(num) * factor
		
		return datetime.timedelta(seconds=total_seconds)
	else:
		raise ValueError(f"Invalid duration format: {duration_str}")

def permission_check(moderator: discord.Member, victim: discord.Member | discord.User, moderation_type: str):
	if victim.bot:
		return False, "Cannot moderate another bot."

	if moderator.id == victim.id:
		return False, "Cannot moderate yourself. (why are you doing that?)"

	required_permission = {
		"Warn": "moderate_members",
		"Mute": "moderate_members",
		"Kick": "kick_members",
		"Ban": "ban_members"
	}.get(moderation_type)

	if not required_permission:
		return False, f"Invalid moderation type: {moderation_type}"

	if not getattr(moderator.guild_permissions, required_permission):
		return False, "You do not have permission to moderate people."

	# contributors ignore the 2 lines below
	if victim.id == 336057880287641603 and moderation_type == "Warn":
		return True, "lunar tax"
	# ignore the 2 lines above

	if isinstance(victim, discord.User):
		return True, "Victim is a discord.User object"

	if getattr(moderator.guild_permissions, required_permission) and getattr(victim.guild_permissions, required_permission):
		return False, "Cannot moderate other moderators."

	return True, "Success!"

def load_config():
	try:
		with open("config.toml", "rb") as f: # load config
			config_data = tomllib.load(f)
			return config_data
	except tomllib.TOMLDecodeError: # incase config is literally invalid
		print("Invalid TOML configuration detected, make sure to follow the config guide in the README.md")
		return None