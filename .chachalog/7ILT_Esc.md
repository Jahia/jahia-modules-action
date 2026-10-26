---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Changed the AI issue agent so it can push a branch with `git -C`, open a draft pull request through cortex's `gh-wrapper`, and edit a trail comment. The permission lists now deny an option inserted into those three commands, and a delete refspec in both `git push` spellings.
