---
name: Discord server 2FA
description: Discord server security requirements that affect bot moderation actions.
---

Discord error `60003` (`Two factor is required for this operation`) is distinct from
a missing channel permission. A server-level requirement for 2FA can block a bot
from creating channels or roles even when its permission overwrites and role
permissions appear correct.

**Why:** The PCF server returned error 60003 while the bot was creating the private
AI channel and also while startup attempted to create helper roles.

**How to apply:** Check for error code 60003 before reporting missing permissions.
An administrator must adjust the server's 2FA security requirement or pre-create
resources; changing the bot's permission overwrites alone will not resolve it.