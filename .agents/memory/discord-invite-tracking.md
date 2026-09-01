---
name: Discord invite tracking
description: Reliability constraint for assigning roles based on Discord invite usage.
---

Discord may dispatch a member-join event before the invite endpoint reports the increased usage count. Invite attribution must compare successive cached snapshots with a short bounded retry window.

**Why:** A single snapshot taken immediately during `on_member_join` can miss the usage delta and prevent the inviter from receiving the eligibility role.

**How to apply:** Keep a startup/event invite baseline, refresh it after each comparison, retry briefly when no delta is found, and log whether role assignment succeeded. Fail without guessing the inviter when Discord does not expose enough data.