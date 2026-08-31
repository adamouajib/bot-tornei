---
name: Discord typing API
description: The discord.py v2 pattern for keeping a channel typing indicator active.
---

Use `async with channel.typing():` around long-running response work. Do not call `channel.trigger_typing()`.

**Why:** Current discord.py versions removed `trigger_typing` from channel objects, which otherwise raises an `AttributeError` during AI responses.

**How to apply:** Keep typing scope around the queue wait and provider request, and let the library manage the indicator lifecycle.