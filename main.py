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
import os
import asyncio
from discord.ext import commands
from pathlib import Path
from utils import utils
from cogwatch import Watcher
import datetime
import sys

base_dir = Path(__file__).resolve().parent

class bot(commands.Bot):
	def __init__(self) -> None:
		intents = discord.Intents.all()
		intents.emojis_and_stickers = False
		allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)
		super().__init__(
			intents=intents,
			max_messages=5000,
			command_prefix="Vinny",
			allowed_mentions=allowed_mentions,
			activity=discord.Activity(type=discord.ActivityType.watching, name="1,000 members")
		)

bot = bot()

tree = bot.tree

config_data = utils.load_config()
token = config_data['discord']['token']
intents = discord.Intents.default()

@bot.event
async def on_ready():
	print(f'logged in to {bot.user}')
	await bot.change_presence(
		activity=discord.Activity(
			type=discord.ActivityType.watching,
			name=f"{len(bot.users):,} members"
		)
    )
	bot.start_time = datetime.datetime.now(datetime.UTC)
	watcher = Watcher(bot, path='cogs', debug=False)
	await watcher.start()

async def loadcogs():
	command_path = base_dir / 'cogs/cmds'
	for files in os.listdir(command_path):
		if files.endswith(".py"):
			await bot.load_extension(f'cogs.cmds.{files[:-3]}')
	extensions_path = base_dir / 'cogs/exts'
	for files in os.listdir(extensions_path):
		if files.endswith(".py"):
			await bot.load_extension(f'cogs.exts.{files[:-3]}')

async def init():
	async with bot:
		await loadcogs()
		await bot.start(token)

asyncio.run(init())