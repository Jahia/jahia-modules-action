---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed the Java dependency and license check comparing a pull request against the repository's default branch instead of the branch the pull request actually targets.

Pull requests aimed at a maintenance branch, or at another pull request's branch, were reported the differences between those two lines rather than their own changes, which could hide the dependency change the pull request really made.
