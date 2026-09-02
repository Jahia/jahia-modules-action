---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

The `runner-cleanup` action no longer removes anything related to Java: `/usr/lib/jvm` (the runner's pre-installed JDKs) is kept, and the hostedtoolcache cleanup now skips any Java/JDK entries. Jahia builds rely on the JDKs present on the runner.
