# PCF™ Discord Bot

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
- Tournament registration requires the member to have used one of their Discord invites to bring at least one person into this server. The bot needs the **Manage Server** permission to verify invite usage; it does not require members to join another server.
- `/warn` and `/time` require an Admin role; `/time` sends the timed-out member a persistent DM with the reason, readable duration, end time, and live remaining-time indicator. `/giveaway` requires a Manager role.
- Normal tournament/event commands are available to Host Staff and higher roles. Big tournament/event and economy commands require Admin or higher, or the Discord Administrator permission.
- Adam (`1338274535325175810`) and Piccolofe (`1012712686770995201`) are the only owners and control system commands such as `:set-log`, `:leaderboard`, `:staff-lb`, and `:machine`.
- `:machine` is owner-only and publishes the persistent Slot Machine panel. Members use its `🎰 spin!!` button; each spin costs 200 Ruby. The displayed odds are 0.5% jackpot (3x 💎 or 777, paying 5,000 Ruby + 50 Crystals), 14.5% big win (three matching symbols, paying 1,500 Ruby), 35% small win (two matching symbols, paying 400 Ruby), and 50% loss (0 Ruby). A jackpot grants the `🎰 Jackpot Winner` role.
- `:1v1 @member <ruby_amount>` starts a staked duel. The challenge embed shows the Ruby stake and total pot; after acceptance, both players pay the same stake, the bot creates an English private thread containing both players, and staff records the winner, who receives the full pot. The match rules tell players to ping Staff as soon as the match ends; winner buttons are staff-only.
- `:give` supports Ruby, Crystals, Ranked Points, and Gems; only Managers/owners can distribute Gems.
- The legacy `:add-rubini`, `:remove-rubini`, and `:add-cristalli` commands are removed.
- `GEMINI_API_KEY` must be present for the private AI channel created by `:start`. The assistant calls the configured AI service asynchronously through `aiohttp`, using bounded HTTP connections, per-user serialization, a persistent Discord typing indicator and automatic 429 retries after 2 seconds, up to three total attempts. Rate-limit details are never shown to users.
- Every question in the private AI channel receives a fresh Gemini-generated answer in the user's latest language; there are no canned question/answer templates. The system instruction includes a detailed structured handbook for tournaments, Big Tournaments, Big Events, Flash Events, Slot Machine, staff, shop, currencies, account linking and rewards, plus the live command/help registries and current active-event status.
- The complete Gemini prompt has a local budget of approximately 200,000 tokens, including the detailed server handbook, live command/help registries, safe project metadata, and recent conversation history. Python source files are excluded, and requests above this budget are rejected before they reach the API.
- Python source files are never sent to Gemini. Environment files, runtime database/session data, archives, internal agent files, credentials and binary assets are excluded from the supplemental project metadata.
- Direct messages do not use the AI assistant; normal DM messages instruct members to use `:start`, which opens the private AI channel in the server. `:link` only shows the account-link setup: members must go to channel `1542227301322719314` and use its button. Support, report and staff-application tickets use the buttons in channel `1147528589676380181`; normal members should not run `:add-ticket`. Staff applications do not require Supporter status; members should be active in the server and apply through the ticket panel. `:boost` displays booster perks only and does not perform a boost.
- `:set-log #channel` records command activity, slash/component interactions, sanctions, DM AI traffic, and uncaught errors for the configured server.
- `:stumble-top` and `/stumble-top` show only the 1v1 leaderboard, including each member's handle, matches played, 1v1 wins, and Rubies won. The separate `:1v1-leaderboard` command shows the same duel leaderboard, and `:set-1v1-leaderboard #channel` configures its independent automatic channel. Both leaderboard flows resolve uncached members through the Discord API, use the stored profile username during API failures, and omit profiles confirmed to have left the server.
- `:set-tw #channel` is Admin-only and stores the single Discord channel used for the `piccolofe` Twitch dashboard. The dashboard polls every 3 minutes, records chatters' total minutes in `db.json`, and changes to `⚪ LIVE ENDED` when the stream finishes.
- Twitch tracking uses the `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` Replit Secrets for the Twitch OAuth client-credentials flow. Admins register the three-part Ruby/Crystals/Gems reward with `:log-tw <amount> <currency> <amount> <currency> <amount> <currency>`; `:claim-tw <twitch_name>` awards it after a completed stream when the viewer has at least 30 tracked minutes.
- The shop uses the persistent panel in the designated shop channel for W items, Gems packages, and Ruby/Crystal exchanges. Members must use its buttons; `:shop` and `:test` are no longer available commands. Gems packages are 100 Gems for 1,000 Crystals, 250 Gems for 2,200 Crystals, 500 Gems for 4,500 Crystals, and 1,000 Gems for 8,000 Crystals. The Gems page no longer displays the small `:link` footer; the account check remains enforced when a Gems purchase is submitted.
- `:setup-shop` is admin-only and replaces old shop panels in the current channel with one persistent three-embed panel. Its `W Items`, `Gems`, and `Exchange` buttons remain active after bot restarts and open private purchase flows.
- `:chest` is owner-only and publishes the persistent Mystery Chest panel. Each opening costs 500 Ruby; the reward odds are 60% Common (300–800 Ruby), 30% Rare (1,200–2,500 Ruby), and 10% Legendary (20–50 Crystals). A legendary reward grants the `📦 Unboxer Supremo` role.
- Giveaway participant counts are updated in the original embed. When a giveaway ends, the result embed stays clean and the winners are pinged in a separate message.
- Drops use `:drop <people> <amount> <currency>` (Ruby, Crystals, Gems, or Ranked Points), remove the drop image, and update the embed with everyone who claimed the reward.
- The AI handbook treats the Twitch live as a Ruby, Crystals and Gems earning route: visible Twitch chatters accumulate time every 3 minutes, staff registers all three amounts with `:log-tw`, and after the live ends each viewer can claim the configured reward once with `:claim-tw <twitch_name>` after reaching 30 minutes. It does not award XP or Ranked Points automatically.
- The supplied PCF Tournament and Shop artwork is included in `bot.zip`; Discord embeds currently use a valid HTTPS fallback because Discord rejects local filesystem paths as image URLs.

## Runtime data

The bot stores profiles, balances, tournament state, events, economy data, and
perk cooldowns in the local `pcf.sqlite3` database. Profile and cooldown writes
commit directly to SQLite; other state is persisted by `save_db()`. SQLite and
its WAL files are runtime data and are excluded from version control.

The older `db.json` file is read only as a one-time migration source when the
SQLite schema has not been initialized.

## Persistent buttons

All buttons have explicit custom IDs. Persistent public panels and ticket /
verification controls are registered with `bot.add_view(...)` during
`on_ready()`, and ticket routing context is restored from SQLite so existing
ticket buttons continue working after a bot restart.

Tournament registration announcements currently ping `@everyone` for every
tournament type. This is controlled by the temporary
`TOURNAMENT_EVERYONE_PING_ENABLED` setting in `main.py`.