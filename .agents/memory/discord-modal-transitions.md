---
name: Discord modal transitions
description: Constraint for multi-step Discord modal flows.
---

Discord modal submissions should not respond by opening another modal directly. Use an ephemeral confirmation message with a button, then open the next modal from that button interaction.

**Why:** The Big Tournament setup stalled when its step-two modal tried to send the prize modal as the same interaction response.

**How to apply:** For any multi-step modal flow, persist the step context, respond to the modal submission with a short-lived view, validate the initiating user on its button callback, and open the next modal there.