# Stumble™ Discord Bot

## Run

The project runs as a Python Discord bot through the `Discord bot` workflow:

```bash
python main.py
```

The workflow is configured as a console process and starts automatically. The bot requires the `DISCORD_TOKEN` secret in Replit Secrets. Never place the token in source files or commit it.

Dependencies are managed by `pyproject.toml` and `uv.lock`; the primary runtime dependency is `discord.py`.

## Runtime data

The bot stores profiles, tournament state, events, and economy data in the local `db.json` file. This file is generated at runtime and is excluded from version control.