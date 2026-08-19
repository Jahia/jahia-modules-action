---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Fixed the pull-request Sonar analysis failing at random while it downloaded its analyzers.

The `sonar-analysis` job of the `reusable-on-code-change` workflow now runs in the pre-warmed `jahia-docker-mvn-cache` container, so the analyzers are read from the image instead of being downloaded from the SonarQube server on every run. The image can be changed with the new `sonar_analysis_container_image` input.
