---
name: Rapid AI chat turns
description: Conversation behavior for users who send several private AI messages in quick succession.
---

Rapid messages in the private AI channel should be collected during a short quiet period and answered as one conversational turn, rather than generating one reply per message.

**Why:** Users often send a greeting and a follow-up immediately; separate responses make the bot appear to interrupt itself and can create avoidable request/rate-limit errors.

**How to apply:** Preserve the debounce window, per-user serialization, and a persistent typing indicator across both the waiting period and the AI request. New messages received during generation should form the next queued turn.

The batch processor should return whether it already handled a user-visible
response, including expected failures and partial multi-message sends. The
debounce task must only send its generic fallback when that result is false.

**Why:** A second outer error message can appear after Gemini succeeded if a
later chunk send or audit-log operation raises.

**How to apply:** Keep response delivery state explicit at the queue boundary
whenever the processor catches delivery or logging exceptions.