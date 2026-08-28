---
name: Imported Python dependency bootstrap
description: Environment behavior seen when starting imported Python workflows.
---

Imported Python projects can have complete dependency declarations while the
Replit runtime still lacks the installed packages at first workflow start.

**Why:** The imported Discord bot declared Flask and its other runtime
dependencies, but the first workflow launch failed during the initial import
until the declared Python packages were installed in the workspace.

**How to apply:** When an imported Python workflow fails with a missing module,
install the packages already declared by the project before changing application
code or its architecture. After installation, inspect the dependency diff because
the package helper can append duplicate entries to an existing requirements file.