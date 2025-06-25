# Vinny
Self-hosted moderation bot

<img src="https://i.imgur.com/mCpZPcv.png" alt="vinny mascot, made by @catneptune on github" width=200, height=200>

### Features
- Moderation tracking
- Tempban support
- Event logs
- Ban appeals
- Tickets & Ticket Panels
- Quickmod (right click message -> Apps -> Quickmod)
- Moderation marking (the ability to mark moderations as active or inactive)

### Dependencies
- **Atleast Python 3.11**
- discord.py
- discord.py-pagination
- Flask (flask[async])
- Flaskcord
- better-ipc
- humanfriendly
- cogwatch
- schedule

### Setup
Begin by cloning the repository
```
git clone https://github.com/PolariteMC/Vinny
cd Vinny
```
Install required dependencies
```
pip install -r requirements.txt
```
Configure the bot token (configuration guide below), and start the bot
```
python ./main.py
```

### Configuration guide
The configuration is just a simple toml file, all you have to do is copy `config.toml.sample` into `config.toml`, and then add the bot token to the `token` key under the `[discord]` table and (at your option), add a custom database file value.

Example:
```toml
[discord]
token = "MjEzMjkwMTY3NDA5MTgwNjcy.8JFhmK.nMMfj8laiN6kknmbPIEtrfr4nk99_4rEDxles"
secret = "D472Ab-1beb138c633029f8d82e800a0025d2e5ded15" # Client secret (for OAuth2), only necessary when using dashboard
id = "1251165854343626752" # Client ID, only necessary if using the dashboard

[database]
file = "moderation.db" # if the user wants to place a database within a directory, they'll need to create that directory in advance

[dashboard] # EVERYTHING UNDER HERE IS ONLY NECESSARY IF YOU'RE USING THE DASHBOARD
url = "https://127.0.0.1:5000" # Set to appropriate URL
ipc_secret = "Vinny - simple moderation bot" # Set to a secret key, important so that the IPC traffic is encrypted.
secret = "Vinny - simple moderation bot" # IMPORTANT! This is used to encrypt cookies.
```
(token and secrets for demonstration purposes, they aren't real)

# Dashboard setup
We have a fairly modern dashboard out of the box, which you can launch by executing the following command:
```bash
python3 dashboard/dashboard.py # IMPORTANT! You must execute the dashboard from project root! Preferably use a WSGI server to run the dashboard.
```

### What you get
- [Bulma](https://bulma.io/)-based web dashboard
- Per-server paginated moderations overview
- Server-toggleable features
- Detailed ticket logs

### TODO:
- None (for now)