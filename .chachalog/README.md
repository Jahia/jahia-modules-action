# Chachalog Changelog Validation

This workflow implements automatic changelog validation for pull requests using [chachalog](https://github.com/GauBen/chachalog).

## How it works

When a pull request is opened, edited, or synchronized, the `changelog-validation` job will:

1. **Check for skip label**: If the PR has a `skip-changelog` label, changelog validation is skipped and any existing chachalog comment is removed.

2. **Check for changelog entries**: If no skip label is present, the job looks for markdown files in `.chachalog/` directory (excluding `intro.md`).

3. **Handle missing entries**: If no changelog entries are found:
   - Adds a comment to the PR prompting the user to add a changelog entry
   - The workflow step fails (other checks continue to run)

4. **Handle existing entries**: If changelog entries are found:
   - The workflow step passes
   - Any existing chachalog prompting comment is removed

## Configuration

The workflow uses the chachalog configuration file at `.chachalog/config.mjs` which includes the GitHub plugin for PR comment management.

## Changelog entry format

Changelog entries should be markdown files in the `.chachalog/` directory with frontmatter specifying the version bump:

```markdown
---
bump: patch
---

# Fix bug in user authentication

Fixed an issue where users couldn't log in with special characters in their password.
```

## Skip changelog requirement

To skip the changelog requirement for a PR, add the `skip-changelog` label. This is useful for:
- Documentation-only changes
- CI/DevOps changes
- Internal refactoring that doesn't affect users

## Integration

This validation is integrated into the `reusable-delivery-pr-chores.yml` workflow and runs automatically for repositories that use this workflow.