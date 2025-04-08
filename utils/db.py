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

import sqlite3
from pathlib import Path
from datetime import datetime
from utils import utils

config_data = utils.load_config()
db_file = config_data['database']['file']

database = Path(__file__).resolve().parent.parent.joinpath(db_file)

def db_connect():
	conn = sqlite3.connect(database)
	c = conn.cursor()

	return conn, c

def create_moderation_table():
	conn, c = db_connect()

	c.execute('''CREATE TABLE IF NOT EXISTS moderations (
						moderation_id INTEGER PRIMARY KEY AUTOINCREMENT,
						guild_id INTEGER,
						user_id INTEGER,
						moderator_id INTEGER,
						moderation_type TEXT,
						reason TEXT,
						severity TEXT,
						time TEXT,
						duration INTEGER,
		   				active BOOLEAN,
						tempban_active BOOLEAN,
						escalated BOOLEAN
					)''')
	c.execute("PRAGMA table_info(moderations)")
	columns = [column[1] for column in c.fetchall()]
	
	new_columns = {
		'escalated': "BOOLEAN"
	}

	for column in new_columns:
		if column not in columns:
			c.execute(f'''
				ALTER TABLE moderations ADD COLUMN {column} {new_columns[column]}
			''')

	conn.commit()
	conn.close()

def create_guilds_table():
	conn, c = db_connect()

	c.execute('''CREATE TABLE IF NOT EXISTS guilds (
					guild_id INTEGER PRIMARY KEY,
					log_channel_id INTEGER DEFAULT NULL,
					event_log_channel_id INTEGER DEFAULT NULL,
		   			appeals_channel_id INTEGER DEFAULT NULL,
					nonce_filter BOOLEAN DEFAULT 0,
					bot_filter BOOLEAN DEFAULT 1,
					on_message_delete BOOLEAN DEFAULT 1,
					on_message_edit BOOLEAN DEFAULT 1,
					on_member_join BOOLEAN DEFAULT 1,
					on_member_leave BOOLEAN DEFAULT 1,
					on_member_update BOOLEAN DEFAULT 1,
					on_guild_channel_create BOOLEAN DEFAULT 1,
					on_guild_channel_delete BOOLEAN DEFAULT 1,
					max_moderations_enabled BOOLEAN DEFAULT 0,
					max_s1_moderations INTEGER DEFAULT 1,
					max_s2_moderations INTEGER DEFAULT 4,
					max_s3_moderations INTEGER DEFAULT 1,
					appeals BOOLEAN DEFAULT 0,
					appeals_message TEXT DEFAULT 'New ban appeal',
					appeals_website_message TEXT DEFAULT 'Please write in detail why you think you should be unbanned',
					appeals_poll BOOLEAN DEFAULT 1
				)''')

	c.execute("PRAGMA table_info(guilds)")
	columns = [column[1] for column in c.fetchall()]
	
	new_columns = {
		'nonce_filter': ["BOOLEAN", 0], 'bot_filter': ["BOOLEAN", 1], 'on_message_delete': ["BOOLEAN", 1], 
		'on_message_edit': ["BOOLEAN", 1], 'on_member_join': ["BOOLEAN", 1], 'on_member_leave': ["BOOLEAN", 1],
		'on_member_update': ["BOOLEAN", 1], 'on_guild_channel_create': ["BOOLEAN", 1], 'on_guild_channel_delete': ["BOOLEAN", 1],
		'max_moderations_enabled': ["BOOLEAN", 0], 'max_s1_moderations': ["INTEGER", 1], 'max_s2_moderations': ["INTEGER", 4],
		'max_s3_moderations': ["INTEGER", 1], 'appeals': ["BOOLEAN", 0], 'appeals_channel_id': ["INTEGER", 0],
		'appeals_message': ["TEXT", "'New ban appeal'"], 'appeals_website_message': ["TEXT", "'Please write in detail why you think you should be unbanned'"],
		'appeals_poll': ["BOOLEAN", 1]
	}

	for column in new_columns:
		if column not in columns:
			c.execute(f'''
				ALTER TABLE guilds ADD COLUMN {column} {new_columns[column][0]} DEFAULT {new_columns[column][1]}
			''')

	conn.commit()
	conn.close()

def create_appeals_table():
	conn, c = db_connect()

	c.execute('''CREATE TABLE IF NOT EXISTS appeals (
						appeal_id INTEGER PRIMARY KEY AUTOINCREMENT,
						guild_id INTEGER,
						user_id INTEGER,
						active BOOLEAN,
						cooldown BOOLEAN,
						banned BOOLEAN,
						time TEXT
					)''')

	new_columns = {
		'banned': ["BOOLEAN", 0]
	}

	c.execute("PRAGMA table_info(guilds)")
	columns = [column[1] for column in c.fetchall()]

	for column in new_columns:
		if column not in columns:
			c.execute(f'''
				ALTER TABLE appeals ADD COLUMN {column} {new_columns[column][0]} DEFAULT {new_columns[column][1]}
			''')

	conn.commit()
	conn.close()

create_guilds_table()
create_appeals_table()
create_moderation_table()

def insert_moderation(guild_id: int, user_id: int, moderator_id: int, moderation_type: str, reason: str, severity: str, time: str, duration: str, conn: sqlite3.Connection, c: sqlite3.Cursor):
	try:
		# we increment the case/moderation id
		c.execute("SELECT MAX(moderation_id) AS max_id FROM moderations")
		result = c.fetchone()
		case_id = 1 if result[0] == None else result[0] + 1
		
		c.execute('''INSERT INTO moderations (moderation_id, guild_id, user_id, moderator_id, moderation_type, reason, severity, time, duration, active, tempban_active, escalated)
					VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (case_id, guild_id, user_id, moderator_id, moderation_type, reason, severity, time, duration, True, True, False))
		conn.commit()
		return case_id
	except Exception as e:
		print(f"Error while inserting moderation: {e}")

def get_count_of_moderations(c: sqlite3.Cursor):
	c.execute("SELECT COUNT(*) FROM moderations")
	count = c.fetchone()[0]
	return count

def get_active_tempbans(conn, c: sqlite3.Cursor): # this gave me a headache, TLDR: checks for "active" tempbans
	c.execute("SELECT moderation_id, time, duration FROM moderations WHERE severity='S3' AND tempban_active=true")
	results = []
	for row in c.fetchall():
		moderation_id = row[0]
		time_unix = float(row[1])
		duration_str = row[2]
		try:
			duration_td = utils.parse_duration(duration_str)
		except Exception as e:
			set_tempban_inactive(moderation_id, conn, c) # fix pre-hotfix invalid timeframes
			continue
		time_obj = datetime.fromtimestamp(time_unix)
		updated_time = time_obj + duration_td # hooray, we now have a datetime object of when the user is supposed to be banned
		results.append({
			'moderation_id': moderation_id,
			'unban_time': updated_time
		})
	return results # have fun with these, main.py! i know you'll make good use of these results

def get_moderation_by_id(moderation_id, c: sqlite3.Cursor):
	c.execute('SELECT * FROM moderations WHERE moderation_id=?', (moderation_id,))
	moderation = c.fetchone()
	return moderation

def set_moderation_inactive_or_active(moderation_id, active: bool, conn: sqlite3.Connection, c: sqlite3.Cursor):
	c.execute('UPDATE moderations SET active=? WHERE moderation_id=?', (active, moderation_id,))
	conn.commit()

def set_tempban_inactive(moderation_id, conn: sqlite3.Connection, c: sqlite3.Cursor):
	c.execute('UPDATE moderations SET tempban_active=0 WHERE moderation_id=?', (moderation_id,))
	conn.commit()

def set_moderation_escalated(moderation_id, conn: sqlite3.Connection, c: sqlite3.Cursor):
	c.execute('UPDATE moderations SET escalated=1 WHERE moderation_id=?', (moderation_id,))
	conn.commit()

def get_moderations_by_user_and_guild(guild_id: int, user_id: int, inactive: bool, c: sqlite3.Cursor):
	if not inactive:
		c.execute("SELECT * FROM moderations WHERE guild_id=? AND user_id=? AND active=1", (guild_id, user_id,))
	else:
		c.execute("SELECT * FROM moderations WHERE guild_id=? AND user_id=?", (guild_id, user_id,))
	moderations = c.fetchall()
	return moderations

def get_moderations_by_user_and_guild_and_sanction(guild_id: int, user_id: int, sanction: str, c: sqlite3.Cursor):
	if sanction in ("S2", "S3"):
		c.execute("SELECT * FROM moderations WHERE guild_id=? AND user_id=? and severity=? AND active=1", (guild_id, user_id, sanction,))
	elif sanction in ("S1", "S4"):
		c.execute("SELECT * FROM moderations WHERE guild_id=? AND user_id=? and severity=? AND active=1 AND escalated<>1", (guild_id, user_id, sanction,))
	moderations = c.fetchall()
	return moderations

def get_moderations_by_guild(guild_id: int, c: sqlite3.Cursor):
	c.execute("SELECT * FROM moderations WHERE guild_id=?", (guild_id,))
	moderations = c.fetchall()
	return moderations

def get_config_value(guild_id: int, key: str, c: sqlite3.Cursor, default: int = 1) -> int:
	try:
		c.execute(f'SELECT {key} FROM guilds WHERE guild_id=?', (guild_id,))
		value = c.fetchone()[0]
		if value is None:
			return default
		return value
	except Exception:
		return default

def set_config_value(guild_id: int, key, value, conn: sqlite3.Connection, c: sqlite3.Cursor):
	c.execute(f"UPDATE guilds SET {key}=? WHERE guild_id=?", (value, guild_id,))
	conn.commit()