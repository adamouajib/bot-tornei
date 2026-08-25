---
name: Keep-alive bootstrap
description: The Discord bot relies on a Flask and nest_asyncio bootstrap block at the very start of main.py.
---

The Flask `keep_alive()` server and `nest_asyncio.apply()` bootstrap at the beginning of `main.py` are intentional runtime infrastructure and must be preserved when the bot is modified or the distributable archive is rebuilt.

**Why:** The bot-hosting environment uses the background Flask endpoint to keep the process awake, while `nest_asyncio` prevents event-loop conflicts between Discord and the AI features.

**How to apply:** Keep the complete bootstrap block at the top of `main.py`, and keep the copy inside `bot.zip` synchronized with the project version.