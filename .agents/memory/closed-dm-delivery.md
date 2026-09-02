---
name: Closed-DM delivery
description: Durable rule for handling Discord direct-message failures consistently.
---

User-facing Discord DMs should go through a single helper that catches `discord.Forbidden` and reports the closed-DM state in the originating channel when one exists. Callers that create pending state or tickets must treat a `None` result as delivery failure and clean up that state.

**Why:** Discord can reject a DM even when the originating interaction succeeds; silently swallowing the exception leaves users with incomplete flows and stale pending records.

**How to apply:** Use the helper for new DM sends, pass the originating channel for actionable feedback, and only continue with “sent” state after it returns a message.