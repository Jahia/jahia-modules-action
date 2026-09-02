---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added a new `runner-cleanup` action, a local copy of [mathio/gha-cleanup](https://github.com/mathio/gha-cleanup) that reclaims ~30 GB of disk space on GitHub-hosted runners. Compared to upstream it adds a `remove-docker-images` input (set it to `false` to keep Docker images pre-pulled on the runner instead of pruning them) and logs, after each element being cleaned up, the amount of disk space reclaimed. It also logs a detailed inventory of the Docker cache (images by name:tag, containers with their image, volumes, build cache) before the prune step.
