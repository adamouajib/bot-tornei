# Stumble™ Discord Bot

## Run

The project runs as a Python Discord bot through the `Discord bot` workflow:

```bash
python main.py
```

The workflow is configured as a console process and starts automatically. The bot requires the `DISCORD_TOKEN` secret in Replit Secrets. Never place the token in source files or commit it.

Dependencies are managed by `pyproject.toml` and `uv.lock`; the primary runtime dependency is `discord.py`.

## Commands and permissions

- `/warn`, `/time`, and `/giveaway` are native Discord slash commands. Slash commands are synced when the bot becomes ready.
- `/warn` and `/time` require an Admin role; `/giveaway` requires a Manager role.
- Normal tournament/event commands are available to Host Staff and higher roles. Big tournament/event and economy commands require Admin or higher.
- Adam (`1338274535325175810`) and Piccolofe (`1012712686770995201`) are the only owners and control system commands such as `:set-log`, `:leaderboard`, `:staff-lb`, and `:machine`.
- `:give` supports Ruby, Crystals, Ranked Points, and Gems; only Managers/owners can distribute Gems.
- The legacy `:add-rubini`, `:remove-rubini`, and `:add-cristalli` commands are removed.
- `GROQ_API_KEY` must be present for DM AI. Requests are serialized per user, show Discord typing status, and retry transient/rate-limit failures up to three times.
- `:set-log #channel` records command activity, slash/component interactions, sanctions, DM AI traffic, and uncaught errors for the configured server.

## Runtime data

The bot stores profiles, tournament state, events, and economy data in the local `db.json` file. This file is generated at runtime and is excluded from version control.