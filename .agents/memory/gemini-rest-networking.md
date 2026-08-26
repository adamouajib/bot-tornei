---
name: Gemini REST networking
description: Hosting-network guidance for Gemini calls in this Discord bot.
---

Use the Gemini `generateContent` REST endpoint through one reusable `aiohttp` session with explicit connect, socket, and total timeouts. Keep the Discord event loop free of synchronous SDK calls and avoid awaiting per-message Discord channel edits before generation.

**Why:** The hosted bot observed Gemini SDK model fallbacks timing out while a Discord channel-topic `PATCH` was also delayed by rate limiting. Direct async REST cancellation bounds the network operation, and removing the per-message topic update prevents Discord backpressure from blocking AI delivery.

**How to apply:** Preserve the startup-created REST session, fixed model fallbacks, bounded retries, and in-memory activity tracking. If persistence of activity metadata is needed, update it outside the message-critical path with throttling.