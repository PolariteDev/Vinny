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

# NOTE: If you wanna use my dashboard module without complying with above terms,
# then contact me for inquiries/questions for permission. You will only be able to
# use my commits if you have received permission from me. <0vfx@proton.me>

import datetime
import time
from flask import Flask, Response, render_template, redirect, render_template_string, request, url_for, abort, current_app
from flaskcord import DiscordOAuth2Session, requires_authorization, Unauthorized
from discord.ext.ipc import Client
import json
import html
import sys
import os
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from utils import utils, db, info
from ast import literal_eval
from asyncio import sleep

dashboard_version = "1.5.0"
cached_usernames = {}
cached_avatars = {}

app = Flask(__name__)

config_data = utils.load_config()
app.secret_key = config_data['dashboard']['secret']

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false" # Set to true only in development

app.config["DISCORD_CLIENT_TOKEN"] = config_data['discord']['token']
app.config["DISCORD_CLIENT_SECRET"] = config_data['discord']['secret']
app.config["DISCORD_CLIENT_ID"] = config_data['discord']['id']
app.config["DISCORD_REDIRECT_URI"] = f"{config_data['dashboard']['url']}/callback"

app.config['TEMPLATES_AUTO_RELOAD'] = True

OAuth2 = DiscordOAuth2Session(app)
ipc = Client(secret_key=config_data['dashboard']['ipc_secret'])

@app.errorhandler(404)
def page_not_found(error):
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('html_error.html', user=user, error="404", error_message="Resource not found", title="404 Not found", description="404 Not found"), 404

@app.errorhandler(401)
def page_not_found(error):
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('html_error.html', user=user, error="403", error_message="Unauthorized", title="401 Unauthorized", description="401 Unauthorized"), 401

@app.errorhandler(403)
def page_not_found(error):
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('html_error.html', user=user, error="403", error_message="Forbidden", title="403 Forbidden", description="403 Forbidden"), 403

@app.errorhandler(500)
def page_not_found(error):
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('html_error.html', user=user, error="500", error_message="Internal server error", title="500 Internal server error", description="401 Internal server error"), 403

@app.route('/')
def index():
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('index.html', user=user, authorized=OAuth2.authorized, title=f"Homepage", description=f"Welcome to Vinny! A free and open-source moderation bot based on sanctions", url=f"{config_data['dashboard']['url']}{url_for('index')}")

@app.route('/learnmore')
def learnmore():
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('learnmore.html', user=user, authorized=OAuth2.authorized, title=f"Learn More", description=f"Learn more about Vinny", url=f"{config_data['dashboard']['url']}{url_for('learnmore')}")

@app.route('/privacypolicy')
def privacypolicy():
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	return render_template('privacypolicy.html', user=user, authorized=OAuth2.authorized, title=f"Privacy Policy", description=f"Vinny privacy policy", url=f"{config_data['dashboard']['url']}{url_for('privacypolicy')}")

@app.context_processor
def inject_global_vars():
	return {'dashboard_version': dashboard_version, 'version': info.get_vinny_version()}

@app.route("/login/")
def login():
	return OAuth2.create_session(scope=["identify", "guilds"])

@app.route("/logout/")
def logout():
	OAuth2.revoke()
	return redirect(url_for("index"))

@app.route("/callback/")
def callback():
	try:
		OAuth2.callback()
	except Exception:
		return redirect(url_for("dashboard"))
	return redirect(url_for("index"))

@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
	return redirect(url_for("login"))

@app.route("/dashboard/")
@requires_authorization
async def dashboard():
	user = OAuth2.fetch_user()
	guilds = OAuth2.fetch_guilds() # use cache instead of user.fetch_guilds() to not get rate limited
	bot_guilds = (await (ipc.request("get_guild_ids"))).response
	bot_guilds = literal_eval(bot_guilds)
	guilds_array = []

	for guild in guilds:
		if guild.permissions.administrator:
			guild.status = True if guild.id in bot_guilds else False
			guilds_array.append(guild)

	guilds_array.sort(key=lambda x: x.status == False)
	return render_template("dashboard.html", guilds=guilds_array, user=user, title=f"Dashboard", description=f"View all available servers", url=f"{config_data['dashboard']['url']}{url_for('dashboard')}")

@app.route("/dashboard/server/<int:guild_id>", methods=['POST', 'GET'])
@requires_authorization
async def server_view(guild_id):
	user = OAuth2.fetch_user()
	guild_obj = None
	for guild in OAuth2.fetch_guilds():
		if guild.id == guild_id:
			guild_obj = guild

	guild_name = (await ipc.request("get_guild_name", guild_id=guild_id)).response
	if guild_name is None:
		return redirect(f'https://discord.com/oauth2/authorize?&client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}')

	admin_bool = await ipc.request("check_admin", user_id=user.id, guild_id=guild_id)
	try:
		admin_bool = literal_eval(admin_bool.response)
	except Exception:
		admin_bool = False
	if admin_bool == True:
		pass
	elif admin_bool == False:
		abort(403)
	else:
		return redirect(f'https://discord.com/oauth2/authorize?&client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}')

	guild_channels = await ipc.request("get_guild_channels", guild_id=guild_id)
	guild_categories = await ipc.request("get_guild_categories", guild_id=guild_id)
	conn, c = db.db_connect()
	c.execute("INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild_id,))
	conn.commit()
	if request.method == 'POST':
		form_fields = {
			"log_channel_id": request.form.get("log_channel"),
			"event_log_channel_id": request.form.get("event_log_channel"),
			"nonce_filter": int(request.form.get("nonce_filter", 0)),
			"max_moderations_enabled": int(request.form.get("max_moderations_enabled", 0)),
			"max_s1_moderations": int(request.form.get("max_s1_moderations", 1)),
			"max_s2_moderations": int(request.form.get("max_s2_moderations", 4)),
			"max_s3_moderations": int(request.form.get("max_s3_moderations", 1)),
			"bot_filter": int(request.form.get("bot_filter", 0)),
			"on_message_delete": int(request.form.get("on_message_delete", 0)),
			"on_message_edit": int(request.form.get("on_message_edit", 0)),
			"on_member_join": int(request.form.get("on_member_join", 0)),
			"on_member_leave": int(request.form.get("on_member_leave", 0)),
			"on_member_update": int(request.form.get("on_member_update", 0)),
			"on_guild_channel_create": int(request.form.get("on_guild_channel_create", 0)),
			"on_guild_channel_delete": int(request.form.get("on_guild_channel_delete", 0)),
			"appeals": int(request.form.get("appeals", 0)),
			"appeals_channel_id": request.form.get("appeals_channel"),
			"appeals_message": request.form.get("appeals_message"),
			"appeals_website_message": request.form.get("appeals_website_message"),
			"appeals_poll": int(request.form.get("appeals_poll", 1)),
			"tickets": int(request.form.get("tickets", 0)),
			"tickets_category_id": request.form.get("tickets_category")
		}
		for form in form_fields:
			if form_fields[form] is None:
				continue
			elif form_fields[form] == 0 or form_fields[form] == "0" or form_fields[form] == 1 or form_fields[form] in guild_channels.response or form_fields[form] in guild_categories.response or form in ('max_s1_moderations', 'max_s2_moderations', 'max_s3_moderations', 'appeals_message', 'appeals_website_message'):
				db.set_config_value(guild_id, form, form_fields[form], conn, c)
		db_values = {}
		defaults = {
			"log_channel_id": 0,
			"event_log_channel_id": 0,
			"nonce_filter": 0,
			"bot_filter": 0,
			"on_message_delete": 1,
			"on_message_edit": 1,
			"on_member_join": 1,
			"on_member_leave": 1,
			"on_member_update": 1,
			"on_guild_channel_create": 1,
			"on_guild_channel_delete": 1,
			"max_moderations_enabled": 0,
			"max_s1_moderations": 1,
			"max_s2_moderations": 4,
			"max_s3_moderations": 1,
			"appeals": 0,
			"appeals_channel_id": 0,
			"appeals_message": "New ban appeal",
			"appeals_website_message": "Please write in detail why you think you should be unbanned",
			"appeals_poll": 1,
			"tickets": 0,
			"tickets_category_id": 0
		}
		for key in defaults:
			db_values[f"{key}"] = db.get_config_value(guild_id, key, c, defaults[f"{key}"])
		conn.close()
		return render_template("server.html", guild=guild_obj, user=user, guild_channels=guild_channels.response, saved=True, db_values=db_values, title=f"{guild_name}", description=f"{guild_name} configuration panel", url=f"{config_data['dashboard']['url']}{url_for('server_view', guild_id=guild_id)}", guild_categories=guild_categories.response)
	else:
		db_values = {}
		defaults = {
			"log_channel_id": 0,
			"event_log_channel_id": 0,
			"nonce_filter": 0,
			"bot_filter": 0,
			"on_message_delete": 1,
			"on_message_edit": 1,
			"on_member_join": 1,
			"on_member_leave": 1,
			"on_member_update": 1,
			"on_guild_channel_create": 1,
			"on_guild_channel_delete": 1,
			"max_moderations_enabled": 0,
			"max_s1_moderations": 1,
			"max_s2_moderations": 4,
			"max_s3_moderations": 1,
			"appeals": 0,
			"appeals_channel_id": 0,
			"appeals_message": "New ban appeal",
			"appeals_website_message": "Please write in detail why you think you should be unbanned",
			"appeals_poll": 1,
			"tickets": 0,
			"tickets_category_id": 0
		}
		for key in defaults:
			db_values[f"{key}"] = db.get_config_value(guild_id, key, c, defaults[f"{key}"])
		conn.close()
		return render_template("server.html", guild=guild_obj, user=user, guild_channels=guild_channels.response, saved=False, db_values=db_values, title=f"{guild_name}", description=f"{guild_name} configuration panel", url=f"{config_data['dashboard']['url']}{url_for('server_view', guild_id=guild_id)}", guild_categories=guild_categories.response)

@app.route("/dashboard/server/<int:guild_id>/moderations/")
async def moderations_redirect(guild_id):
	return redirect(url_for('moderations', guild_id=guild_id, page_number=1))

@app.route("/dashboard/server/<int:guild_id>/moderations/page/<int:page_number>")
async def moderations(guild_id, page_number):
	user = None
	if OAuth2.authorized:
		user = OAuth2.fetch_user()

	conn, c = db.db_connect()
	page = 1
	total_pages = 0
	hero_chunk = None
	lock = False
	show_lock = False
	moderations = db.get_moderations_by_guild(guild_id, c)
	conn.close()
	try:
		order = request.args.get('order', default='newest', type=str)
		show_inactive = request.args.get('show_inactive', default='false', type=str)
		moderations = [moderation for moderation in moderations if moderation[9] != 0] if show_inactive == "false" else moderations
		if order == "newest":
			moderations.reverse()
		for i in range(0, len(moderations), 12):
			chunk = moderations[i:i+12]
			total_pages += 1
			if page == page_number and not lock:
				lock = True # so that it correctly paginates
				hero_chunk = []
				for moderation in chunk:
					mutable_moderation = list(moderation)
					if moderation[2] not in cached_usernames:	
						mutable_moderation[2] = (await ipc.request("get_username", user_id=mutable_moderation[2])).response
						cached_usernames.update({moderation[2]: mutable_moderation[2]})
					else:
						mutable_moderation[2] = cached_usernames[moderation[2]]
					if moderation[3] not in cached_usernames:	
						mutable_moderation[3] = (await ipc.request("get_username", user_id=mutable_moderation[3])).response
						cached_usernames.update({moderation[3]: mutable_moderation[3]})
					else:
						mutable_moderation[3] = cached_usernames[moderation[3]]
					mutable_moderation[7] = (datetime.datetime.fromtimestamp(float(moderation[7]), datetime.UTC)).strftime("%Y-%m-%d %H:%M:%S")
					if mutable_moderation[8] is None or mutable_moderation[8] == "N/A":
						mutable_moderation[8] = ""
					if mutable_moderation[9] == 0:
						mutable_moderation[9] = "No"
					else:
						mutable_moderation[9] = "Yes"
					mutable_moderation.append(moderation[2])
					mutable_moderation.append(moderation[3])
					hero_chunk.append(tuple(mutable_moderation))
			elif lock:
				pass
			else:
				page += 1
	except Exception:
		abort(500)
	guild_name = (await ipc.request("get_guild_name", guild_id=guild_id)).response
	if guild_name is None:
		abort(403)
	if hero_chunk is None and page_number == 1:
		return render_template('html_error.html', user=user, error="No moderations found", error_message="This server doesn't have a moderation yet", title="No moderations found", description="No moderations found"), 404
	minimum_page = total_pages - (total_pages - 1)
	if minimum_page <= page <= total_pages:
		pass
	else:
		abort(404)

	return render_template("moderations.html", user=user, guild_name=guild_name, guild_id=guild_id, chunk=hero_chunk, page=page, total_pages=total_pages, page_number=page_number, title=f"Moderations - {guild_name}", description=f"View all moderations in {guild_name}", url=f"{config_data['dashboard']['url']}{url_for('moderations', guild_id=guild_id, page_number=1)}", order=order, show_inactive=show_inactive)

@app.route("/dashboard/server/<int:guild_id>/appeal/", methods=['POST', 'GET'])
async def appeal(guild_id):
	user = None
	guild_name = (await ipc.request("get_guild_name", guild_id=guild_id)).response
	if guild_name is None:
		abort(403)
	conn, c = db.db_connect()
	if db.get_config_value(guild_id, "appeals", c, 0) == 0:
		conn.close()
		abort(404)
	if OAuth2.authorized:
		user = OAuth2.fetch_user()
	else:
		return render_template_string("""
			{% extends "base.html" %}
			{% block content %}
			<div class="hero container">
				<div class="container">
					<p class="title">Unauthorized</p>
					<p class="subtitle">You are not logged in. Please <a href="/login">log in via discord</a> and revisit this page.</p>
				</div>
			</div>
			{% endblock %}
		""", user=user, title=f"Appeal in {guild_name}", description=f"Submit a ban appeal form to {guild_name}'s staff members!", url=f"{config_data['dashboard']['url']}{url_for('appeal', guild_id=guild_id)}")
	ban_status = literal_eval((await ipc.request("get_ban_status", guild_id=guild_id, user_id=user.id)).response)

	if not ban_status:
		return render_template_string("""
			{% extends "base.html" %}
			{% block content %}
			<div class="hero container">
				<div class="container">
					<p class="title">Not Acceptable</p>
					<p class="subtitle">You are not banned from this server.</p>
				</div>
			</div>
			{% endblock %}
		""", user=user, title="406 Not Acceptable", description="403 Not Acceptable", url=f"{config_data['dashboard']['url']}{url_for('appeal', guild_id=guild_id)}"), 406

	if request.method == 'POST':
		c.execute("SELECT appeal_id, guild_id, user_id, active, time FROM appeals WHERE cooldown=true")
		results = c.fetchall()
		for row in results:
			if guild_id and user.id in row:
				return render_template_string("""
					{% extends "base.html" %}
					{% block content %}
					<div class="hero container">
						<div class="container">
							<p class="title">Appeal already submitted</p>
							<p class="subtitle">You cannot send another appeal till your cooldown is over.</p>
						</div>
					</div>
					{% endblock %}
				""", guild_name=guild_name, user=user, title="Appeal submitted", description="Appeal submitted")
		c.execute("SELECT MAX(appeal_id) AS max_id FROM appeals")
		result = c.fetchone()
		appeal_id = 1 if result[0] == None else result[0] + 1

		c.execute("""INSERT INTO appeals (appeal_id, guild_id, user_id, active, cooldown, time)
					VALUES (?,?,?,?,?,?)""", (appeal_id, guild_id, user.id, True, True, str(time.time())))
		conn.commit()
		appeal = request.form["appeal_text"]
		await ipc.request("send_appeal_message", guild_id=guild_id, user_id=user.id, appeal=appeal, appeal_id=appeal_id)
		await sleep(1)
		return render_template_string("""
			{% extends "base.html" %}
			{% block content %}
			<div class="hero container">
				<div class="container">
					<p class="title">Appeal submitted</p>
					<p class="subtitle">Your appeal has been forwarded to {{ guild_name }} moderators.</p>
				</div>
			</div>
			{% endblock %}
		""", guild_name=guild_name, user=user, title="Appeal submitted", description="Appeal submitted")
	else:
		c.execute("SELECT appeal_id, guild_id, user_id, active, time FROM appeals WHERE cooldown=true")
		results = c.fetchall()
		for row in results:
			if guild_id and user.id in row:
				return render_template_string("""
					{% extends "base.html" %}
					{% block content %}
					<div class="hero container">
						<div class="container">
							<p class="title">Appeal already submitted</p>
							<p class="subtitle">You cannot send another appeal till your cooldown is over.</p>
						</div>
					</div>
					{% endblock %}
				""", guild_name=guild_name, user=user, title="Appeal submitted", description="Appeal submitted")
		server_message = db.get_config_value(guild_id, "appeals_website_message", c, "Please write in detail why you think you should be unbanned")
		conn.close()
		return render_template("appeal.html", guild_name=guild_name, user=user, title=f"Submit an appeal in {guild_name}", description=f"Fill in the required form & submit.", server_message=server_message)

@app.route("/dashboard/server/<int:guild_id>/ticket/<int:ticket_id>", methods=["GET","POST"])
@requires_authorization
async def view_ticket(guild_id, ticket_id):
	user = OAuth2.fetch_user()
	mod_bool = await ipc.request("check_mod", user_id=user.id, guild_id=guild_id)
	try:
		mod_bool = literal_eval(mod_bool.response)
	except Exception:
		mod_bool = False
	if not mod_bool:
		abort(403)

	conn, c = db.db_connect()
	c.execute('SELECT reason, active, messages, user_id, time FROM tickets WHERE guild_id=? AND ticket_id=?', (guild_id, ticket_id))
	row = c.fetchone()
	conn.close()
	if not row:
		abort(404)

	reason, active, messages_json, user_id, time_unix = row
	if active:
		abort(403)

	vinny_id = int((await ipc.request("get_bot_id")).response)

	try:
		if messages_json == "deleted":
			msgs = [{
				"timestamp": time_unix,
				"author_id": vinny_id,
				"content": "Ticket content deleted as it was older than 30 days.",
				"deleted": True
			}]
		else:
			msgs = json.loads(messages_json) if messages_json else []
	except json.JSONDecodeError:
		msgs = []

	ticket_log = ""
	last_author = None
	last_ts = None
	group_open = False

	for m in msgs:
		ts = m.get("timestamp")
		author = m.get("author_id")

		author_username = cached_usernames.get(author) or (await ipc.request("get_username", user_id=author)).response
		cached_usernames[author] = author_username

		avatar_url = cached_avatars.get(author) or (await ipc.request("get_user_avatar_url", user_id=author)).response
		cached_avatars[author] = avatar_url

		versions = [m.get("content", "")]
		edits = m.get("edits", {})
		for idx in sorted(edits, key=lambda x: int(x)):
			versions.append(edits[idx]["new"])

		danger_class = " has-text-danger" if m.get("deleted") else ""

		if author != last_author or (last_ts and ts - last_ts > 300):
			if group_open:
				ticket_log += "</div></div>"
				group_open = False

			ticket_log += f"""
				<div style="display: flex; margin-bottom: 1em;">
					<img src="{avatar_url}" alt="{author_username}'s avatar"
						style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">
					<div>
						<strong>{author_username}</strong>
						<span style="color: gray; font-size: 0.9em;">
							at {datetime.datetime.fromtimestamp(int(ts), datetime.UTC).strftime("%d/%m/%Y, %H:%M")} UTC
						</span>
			"""
			group_open = True

		parts = []
		for i, text in enumerate(versions):
			is_last = (i == len(versions) - 1)
			opacity = 1 if is_last else 0.5
			escaped = html.escape(text)
			if is_last and i > 0:
				escaped += ' <span class="has-text-grey" style="font-size: 0.75em;">(edited)</span>'
			parts.append(f'<span style="opacity:{opacity};">{escaped}</span>')
		joined = '<br>'.join(parts)
		ticket_log += f'<p style="margin:4px 0 0 0;" class="{danger_class}">{joined}</p>'

		last_author = author
		last_ts = ts

	if group_open:
		ticket_log += "</div></div>"

	guild_name = (await ipc.request("get_guild_name", guild_id=guild_id)).response
	return render_template('ticket.html', ticket_log=ticket_log, user=user, reason=reason, ticket_id=ticket_id, guild_name=guild_name, guild_id=guild_id, title=f"Ticket #{ticket_id} - {guild_name}", user_name=(await ipc.request("get_username", user_id=user_id)).response, time_unix=datetime.datetime.fromtimestamp(int(time_unix), datetime.UTC).strftime("%d/%m/%Y, %H:%M"))

@app.route("/dashboard/server/<int:guild_id>/ticket/<int:ticket_id>/download", methods=['GET'])
@requires_authorization
async def download_ticket_log(guild_id, ticket_id):
	user = OAuth2.fetch_user()
	mod_bool = await ipc.request("check_mod", user_id=user.id, guild_id=guild_id)
	try:
		mod_bool = literal_eval(mod_bool.response)
	except Exception:
		mod_bool = False
	if not mod_bool:
		abort(403)

	conn, c = db.db_connect()
	c.execute('SELECT messages FROM tickets WHERE guild_id = ? AND ticket_id = ?', (guild_id, ticket_id))
	row = c.fetchone()
	conn.close()

	if not row:
		abort(404)

	messages_json = row[0]
	try:
		msgs = json.loads(messages_json) if messages_json else []
	except json.JSONDecodeError:
		msgs = []

	lines = []
	for m in msgs:
		ts = m.get("timestamp")
		author = m.get("author_id")
		if author in cached_usernames:
			author_username = cached_usernames[author]
		else:
			author_username = (await ipc.request("get_username", user_id=author)).response
			cached_usernames[author] = author_username

		time_str = datetime.datetime.fromtimestamp(int(ts), datetime.UTC).strftime("%d/%m/%Y, %H:%M")
		if m.get("deleted"):
			lines.append(f"{author_username} ({time_str} UTC) - {content} [message deleted]")
		else:
			content = m.get("content", "").replace("\n", " ")
			lines.append(f"{author_username} ({time_str} UTC) - {content}")

		edits = m.get("edits", {})
		for idx in sorted(edits, key=lambda x: int(x)):
			edited = edits[idx].get("new", "").replace("\n", " ")
			lines.append(f"\t> edited (version {idx}): {edited}")

	text_content = "\n".join(lines) or "No messages recorded."

	return Response(text_content, mimetype="text/plain", headers={"Content-Disposition": f"attachment; filename=ticket_{guild_id}_{ticket_id}.txt"})

if __name__ == '__main__':
	app.run()