---
name: Persistent Discord state
description: Design rule for Discord buttons that must keep working after bot restarts.
---

Persistent Discord views need both a static custom ID and a startup-registered view. If a callback depends on message-specific state, the state must be persisted and the callback must resolve it from the interaction channel or message rather than relying only on constructor arguments.

**Why:** Discord can deliver an old button interaction to a newly registered view after a process restart, but the original in-memory view instance and its constructor state no longer exist.

**How to apply:** Keep public panel views stateless where possible. For ticket or verification controls, persist the channel-to-user routing record and make the registered fallback view resolve that record from the database.