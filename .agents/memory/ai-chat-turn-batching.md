---
name: Rapid AI chat turns
description: Conversation behavior for users who send several private AI messages in quick succession.
---

Rapid messages in the private AI channel should be collected during a short quiet period and answered as one conversational turn, rather than generating one reply per message.

**Why:** Users often send a greeting and a follow-up immediately; separate responses make the bot appear to interrupt itself and can create avoidable request/rate-limit errors.

**How to apply:** Preserve the debounce window, per-user serialization, and a persistent typing indicator across both the waiting period and the AI request. New messages received during generation should form the next queued turn.