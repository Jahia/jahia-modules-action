---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed AI bug scoring so the PM Score field holds the plain sum of the points. A bug with a data loss, an unstable platform or a site fully down no longer gets 100 extra points, so a score of 170 now shows 70.
