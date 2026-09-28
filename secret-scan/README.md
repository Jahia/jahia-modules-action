# Secret Scan

Scans the commits of a pull request with [gitleaks](https://github.com/gitleaks/gitleaks), and fails when one of them adds a secret. A secret is a value such as a token, a password or a private key.

The action scans the commits between the base and the head of the pull request, and no other commit. A finding on another branch therefore never fails this pull request. The cost of the scan follows the size of the pull request, and not the size of the repository.

## Usage

The `PR Chores` reusable workflow runs this action on every pull request event except `closed`. A repository that calls that workflow needs nothing else.

To call the action from another workflow:

```yaml
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: jahia/jahia-modules-action/secret-scan@v2
```

The action checks the repository out itself, so the job needs no `actions/checkout` step. It needs no secret, so it also runs on a pull request from a fork.

## Inputs

| Name | Default | Description |
| --- | --- | --- |
| `base_sha` | the base of the pull request | The commit the scanned range starts after. |
| `head_sha` | the head of the pull request | The last commit of the scanned range. |

Outside a pull request event, both inputs are required.

## Configuration

A repository with a `.gitleaks.toml` at its root scans with that file, and a `.gitleaksignore` at its root applies too. See the [gitleaks configuration](https://github.com/gitleaks/gitleaks#configuration) for both formats.

A repository without a `.gitleaks.toml` scans with [`gitleaks.toml`](gitleaks.toml) beside this action. That file keeps the default gitleaks rules. It also allowlists the public local-development defaults that Jahia repositories carry, such as the root password of the Jahia Docker image.

A repository file replaces the base file, and it does not add to it. Start a repository file from a copy of `gitleaks.toml`, then add the entries of the repository.

## When the scan reports a secret

The job log names the file, the commit and the rule of each finding, and it hides the value. Apply the first case that matches:

1. **The value is a real secret.** Stop, and tell the owner of the secret. The secret is already public on a public repository, so its owner rotates it. Removing it from the branch does not remove it from the history.
2. **The value is a test fixture in a commit you can still rewrite.** Build the value in the test by concatenation, such as `"gh" + "p_" + body`, so that no commit carries the literal value. Rewrite the commit, and push again.
3. **The value is a test fixture that must stay as written.** Add a `.gitleaks.toml` at the root of the repository, or add to the existing one, in the same pull request. Give the fixture a narrow regex in an allowlist, with a comment that names the test. A regex allowlists its match in every file of the repository, so it matches the fixture and nothing wider.

## Cost

The checkout fetches every commit and tree, and no file content. The scan then fetches the file contents of the scanned commits only. One private Jahia repository holds 38,000 commits in a 440 MB pack. Its history without file contents weighed 54 MB and took 11 seconds to fetch. A scan of a pull request of one or two commits then took 2 to 4 seconds.

## Making the check required

A job of the `PR Chores` workflow blocks no merge by itself. To block a pull request that adds a secret, add the check to the required status checks of the branch ruleset of the repository. The check is named after the calling job, such as `WF / Secret Scan` for the `Delivery - PR Chores` workflow that `Jahia/.github` manages.

## Limits

- The action detects a secret after the push. A secret on a public repository is public from the moment of the push, and only GitHub push protection keeps it unpublished.
- The action reads the commits of pull requests only. A branch that is pushed without a pull request is not scanned.
- The pinned gitleaks archive is for `x86_64` runners.
