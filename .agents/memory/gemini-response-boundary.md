---
name: Gemini response boundary
description: Durable guidance for preventing internal Gemini analysis from reaching Discord users.
---

The Gemini response cleaner must remain a single, centralized function and must run immediately after every successful response extraction, before the text is embedded, split, or sent to Discord.

**Why:** Prompt-only instructions are not a reliable security boundary, and multiple cleaner definitions can silently override one another in a large single-file bot.

**How to apply:** When adding or changing Gemini model fallbacks, route every `response.text` return through the same cleaner and keep regression coverage for common analysis headers and leading bullets.