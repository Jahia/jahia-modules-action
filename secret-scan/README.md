# Secret Scan

Fails a pull request when one of its commits adds a secret, such as a token, a password or a private key. The action runs [gitleaks](https://github.com/gitleaks/gitleaks) on the commits between the base and the head of the pull request only. A finding on another branch therefore never fails the pull request, and the cost follows the size of the pull request.

## Usage

The `PR Chores` reusable workflow runs the action on every pull request event except `closed`, so a repository that calls that workflow needs nothing else. To call the action from another workflow:

```yaml
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: jahia/jahia-modules-action/secret-scan@v2
```

The action checks the repository out into `.secret-scan`, and the last step removes that directory. The job therefore needs no checkout step and keeps its own sources. The action needs no secret, and it also runs on a pull request from a fork.

## Inputs

| Name | Default | Description |
| --- | --- | --- |
| `base_sha` | the base of the pull request | The commit the scanned range starts after. |
| `head_sha` | the head of the pull request | The last commit of the scanned range. |

Both inputs are required outside a pull request event.

## Configuration

The scan reads its configuration from the base commit, so a pull request cannot relax its own scan. A change to the configuration applies once it merges.

- `.gitleaks.toml` replaces the configuration of the action and does not add to it, so start it from a copy of [`gitleaks.toml`](gitleaks.toml).
- `.gitleaksignore` lists the fingerprints of the findings to skip.
- Without a `.gitleaks.toml`, the scan uses [`gitleaks.toml`](gitleaks.toml). That file keeps the default gitleaks rules and allowlists the public Jahia local-development defaults, such as the root password of the Jahia Docker image. It also allowlists a quoted shell variable used as a curl user, such as `-u "$SONAR_TOKEN:"`, which gitleaks reads as a credential.

The [gitleaks documentation](https://github.com/gitleaks/gitleaks#configuration) describes both formats. A pull request that changes either file gets a warning in its checks. A `CODEOWNERS` entry for the two files makes a reviewer read every change to them.

## When the scan reports a secret

The job log names the file, the commit and the rule of each finding, and it hides the value. Apply the first case that matches:

1. **The value is a real secret.** Stop, and tell its owner, who rotates it. A public repository has already published it, and removing it from the branch does not remove it from the history.
2. **The value is a test fixture in a commit you can still rewrite.** Build the value by concatenation, such as `"gh" + "p_" + body`, then rewrite the commit and push again.
3. **The value is a test fixture that must stay as written.** The pull request of the fixture cannot allowlist it, because the scan reads the configuration of the base. Add the regex in a pull request of its own first:
   1. Open a pull request that adds a regex for the fixture to `.gitleaks.toml`, with a comment that names the test. The regex applies to every file of the repository, so anchor it with `^` and `$` to match the fixture and nothing wider.
   2. To get a green scan before the regex merges, make the branch of the regex the base of the pull request of the fixture. The scan then reads the regex from that base.
   3. Once the regex merges, start a new scan of the fixture with a push, the **Update branch** button or an edit of the title. A re-run of the failed job reads the old base again.

## Cost

The checkout fetches the commits and trees without file contents, and the scan fetches only the contents of the scanned commits. On a private Jahia repository of 38,000 commits and a 440 MB pack, the checkout fetched 54 MB in 11 seconds. The scan of a pull request of one or two commits then took 2 to 4 seconds.

## Making the check required

The check blocks no merge until the branch ruleset of the repository lists it as a required status check. Its name follows the calling job, such as `WF / Secret Scan` for the `Delivery - PR Chores` workflow that `Jahia/.github` manages.

## Limits

- The action detects a secret after the push, when a public repository has already published it. Only GitHub push protection blocks the push itself.
- A branch that is pushed without a pull request is not scanned.
- The pinned gitleaks archive runs on `x86_64` runners only.
