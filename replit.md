# Stumble™ Discord Bot

## Run

The project runs as a Python Discord bot through the `Discord bot` workflow:

```bash
python main.py
```

The workflow is configured as a console process and starts automatically. The bot requires the `DISCORD_TOKEN` secret in Replit Secrets. Never place the token in source files or commit it.

## Hosting

The bot can run through the configured Replit workflow with `python main.py`.

Dependencies are managed by `pyproject.toml` and `uv.lock`; the primary runtime dependency is `discord.py`.

## Commands and permissions

- `/warn`, `/time`, and `/giveaway` are native Discord slash commands. Slash commands are synced when the bot becomes ready.
- `/warn` and `/time` require an Admin role; `/giveaway` requires a Manager role.
- Normal tournament/event commands are available to Host Staff and higher roles. Big tournament/event and economy commands require Admin or higher, or the Discord Administrator permission.
- Adam (`1338274535325175810`) and Piccolofe (`1012712686770995201`) are the only owners and control system commands such as `:set-log`, `:leaderboard`, `:staff-lb`, and `:machine`.
- `:give` supports Ruby, Crystals, Ranked Points, and Gems; only Managers/owners can distribute Gems.
- The legacy `:add-rubini`, `:remove-rubini`, and `:add-cristalli` commands are removed.
- `GEMINI_API_KEY` must be present for the private AI channel created by `:start`. The assistant calls the configured AI service asynchronously through `aiohttp`, using bounded HTTP connections, per-user serialization, a persistent Discord typing indicator and automatic 429 retries after 2 seconds, up to three total attempts. Rate-limit details are never shown to users.
- Every question in the private AI channel receives a fresh Gemini-generated answer in the user's latest language; there are no canned question/answer templates. The system instruction includes a detailed structured handbook for tournaments, Big Tournaments, Big Events, Flash Events, Slot Machine, staff, shop, currencies, account linking and rewards, plus the live command/help registries and current active-event status.
- The complete Gemini prompt has a local budget of approximately 100,000 tokens, including server knowledge and recent conversation history. Python source files are excluded, and requests above this budget are rejected before they reach the API.
- Python source files are never sent to Gemini. Environment files, runtime database/session data, archives, internal agent files, credentials and binary assets are excluded from the supplemental project metadata.
- Direct messages do not use the AI assistant; normal DM messages instruct members to use `:start`, which opens the private AI channel in the server. `:link` only shows the account-link setup: members must go to channel `1542227301322719314` and use its button. Support, report and staff-application tickets use the buttons in channel `1147528589676380181`; normal members should not run `:add-ticket`. Staff applications do not require Supporter status; members should be active in the server and apply through the ticket panel. `:boost` displays booster perks only and does not perform a boost.
- `:set-log #channel` records command activity, slash/component interactions, sanctions, DM AI traffic, and uncaught errors for the configured server.
- `:set-tw #channel` is Admin-only and stores the single Discord channel used for the `piccolofe` Twitch dashboard. The dashboard polls every 3 minutes, records chatters' total minutes in `db.json`, and changes to `⚪ LIVE ENDED` when the stream finishes.
- Twitch tracking uses the `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` Replit Secrets for the Twitch OAuth client-credentials flow. `:claim-tw <twitch_name>` awards 50 Gems after a completed stream when the viewer has at least 30 tracked minutes.
- The supplied PCF Tournament and Shop artwork is included in `bot.zip`; Discord embeds currently use a valid HTTPS fallback because Discord rejects local filesystem paths as image URLs.

## Runtime data

The bot stores profiles, tournament state, events, and economy data in the local `db.json` file. This file is generated at runtime and is excluded from version control.