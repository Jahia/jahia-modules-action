---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Improved the Java dependency and license check, which downloaded the whole Maven repository on every run because the cache it asked for was never written under that name.
