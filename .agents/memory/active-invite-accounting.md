---
name: Active invite accounting
description: Domain constraint for counting only invitees who are currently in a Discord server.
---

Active invite counts cannot be derived reliably from Discord invite usage totals because those totals include members who later leave. Store one durable attribution per current invitee, use an idempotent insert on join, and remove that row on departure before recomputing the inviter's count.

**Why:** Discord exposes invite usage deltas but does not expose a historical list of which current members were invited by each link. A per-invitee record makes member removal restart-safe and prevents duplicate event delivery from double-counting.

**How to apply:** Keep invite-code snapshots only for join attribution. Treat the per-member attribution table as the source of truth for active leaderboard queries, eligibility roles, and `on_member_remove` decrements.