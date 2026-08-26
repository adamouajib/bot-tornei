---
name: GitHub push authentication
description: Environment constraint affecting pushes to the configured GitHub HTTPS remote.
---

The configured GitHub HTTPS remote requires valid authorization before commits can be pushed; local commits can still be created successfully.

**Why:** Repeated push attempts returned GitHub's invalid username or token error, and credentials must not be handled in chat or written to the project.

**How to apply:** Check the workspace's secure GitHub authorization before retrying a push. Do not ask the user to paste a token or alter source files to store credentials.