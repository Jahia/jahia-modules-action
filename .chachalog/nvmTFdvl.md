---
# Allowed version bumps: patch, minor, major
jahia-modules-action: minor
---

Added the `slack-notification` action: the person who pushed gets the result of the PR checks in Slack.

A repository opts in with a workflow that runs on `workflow_run` of its checks, as the README of the action shows.
