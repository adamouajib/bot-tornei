---
name: .replit validation
description: The supported way to remove accidental or temporary .replit changes.
---

Direct edits to `.replit` are rejected by the workspace. Write the complete intended TOML to a temporary file inside the workspace and pass that path to the platform's schema-validation replacement flow.

**Why:** The workspace protects workflow and port configuration from unvalidated edits, while isolated runtime smoke tests can leave temporary port mappings behind.

**How to apply:** Preserve the full existing TOML, remove only the unwanted entries, validate and replace the file, then delete the temporary file and check the final git diff.