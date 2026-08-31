---
name: Private channel permission limits
description: Discord's channel permission overwrite limit and the safe pattern for per-user private channels.
---

Private per-user channels should deny `@everyone` and explicitly allow only the target member and the bot. Do not generate an overwrite for every guild role.

**Why:** Discord accepts at most 100 channel permission overwrites. A guild with many roles can make an otherwise valid channel-create request fail with `Invalid Form Body`.

**How to apply:** Rely on the category's existing deny policy where possible, then add only the `@everyone`, target-user, and bot overwrites needed by the private channel.