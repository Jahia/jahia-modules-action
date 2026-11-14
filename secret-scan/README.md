# Secret Scan

Fails a pull request when one of its commits adds a secret, such as a token, a password or a private key. The action runs [gitleaks](https://github.com/gitleaks/gitleaks) on the commits between the base and the head of the pull request only. A finding on another branch therefore never fails the pull request, and the cost follows the size of the pull request.

## Usage

The `PR Chores` reusable workflow runs the action on every pull request event except `closed`, so a repository that calls that workflow needs nothing else. To call the action from another workflow that runs on a pull request event:

```yaml
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: jahia/jahia-modules-action/secret-scan@v2
```

The action checks the repository out into `.secret-scan`, and the last step removes that directory. The job therefore needs no checkout step and keeps its own sources. The action needs no secret, and it also runs on a pull request from a fork. It downloads gitleaks from the release page of gitleaks, and through the GitHub API with the token of the job when that page fails.

## Configuration

The scan reads its configuration from the base commit, so a pull request cannot relax its own scan. A change to the configuration applies once it merges.

- `.gitleaks.toml` replaces the configuration of the action and does not add to it, so start it from a copy of [`gitleaks.toml`](gitleaks.toml).
- `.gitleaksignore` lists the fingerprints of the findings to skip.
- Without a `.gitleaks.toml`, the scan uses [`gitleaks.toml`](gitleaks.toml). That file keeps the default gitleaks rules and allowlists the public Jahia local-development defaults, such as the root password of the Jahia Docker image. It also allowlists a quoted shell variable used as a curl user, such as `-u "$SONAR_TOKEN:"`, which gitleaks reads as a credential. It also allowlists the public account key of the Azure storage emulator, which `@azure/storage-blob` carries into the `dist/` of an action that bundles `@actions/artifact`. The file adds two rules to the default rules:
  - `url-with-password` reports a URL that carries a password of 4 characters or more in its user part, in the form `scheme://user:password@host/db`. The rule names the schemes `postgres`, `postgresql`, `mysql`, `mariadb`, `mongodb`, `mongodb+srv`, `redis`, `rediss`, `amqp`, `amqps` and `clickhouse`. It does not report a braced variable such as `${DB_PASSWORD}`, an upper-case variable such as `$DB_PASSWORD`, or a placeholder such as `<password>`. It reports the default value of a variable, as in `${DB_PASSWORD:-value}`, because that value is committed.
  - `local-settings-file` reports a commit that adds or changes a file of per-developer settings or credentials, whatever its content. The rule names `.claude/settings.local.json`, `mise.local.toml`, `.netrc`, `.git-credentials` and `.aws/credentials`.

The [gitleaks documentation](https://github.com/gitleaks/gitleaks#configuration) describes both formats. A pull request that changes either file gets a warning in its checks. A `CODEOWNERS` entry for the two files makes a reviewer read every change to them.

## When the scan reports a secret

The job log names the file, the commit and the rule of each finding, and it hides the value. Apply the first case that matches:

1. **The value is a real secret.** Stop, and tell its owner, who rotates it. A public repository has already published it, and removing it from the branch does not remove it from the history.
2. **The finding names a file of per-developer settings, with the rule `local-settings-file`.** Remove the file from each commit of the pull request, add its name to `.gitignore`, then push again. A later commit that deletes the file does not clear the finding, because the scan reads each commit of the pull request. A file of that name that must stay in git, such as a shared template, needs a pull request of its own first. That pull request adds the path of the file to the `paths` of an `[[allowlists]]` entry in `.gitleaks.toml`, such as `'''(?:^|/)mise\.local\.toml$'''`. Once it merges, start a new scan as step 3 of case 4 states.
3. **The value is a test fixture in a commit you can still rewrite.** Build the value by concatenation, such as `"gh" + "p_" + body`, then rewrite the commit and push again.
4. **The value is a test fixture that must stay as written.** The pull request of the fixture cannot allowlist it, because the scan reads the configuration of the base. Add the regex in a pull request of its own first:
   1. Open a pull request that adds a regex for the fixture to `.gitleaks.toml`, with a comment that names the test. The regex applies to every file of the repository, so anchor it with `^` and `$` to match the fixture and nothing wider.
   2. To get a green scan before the regex merges, make the branch of the regex the base of the pull request of the fixture. The scan then reads the regex from that base.
   3. Once the regex merges, start a new scan of the fixture with a push, the **Update branch** button or an edit of the title. A re-run of the failed job reads the old base again.

## Cost

The checkout fetches the commits and trees without file contents, and the scan fetches only the contents of the scanned commits. On a private Jahia repository of 38,000 commits and a 440 MB pack, the checkout fetched 54 MB in 11 seconds. The scan of a pull request of one or two commits then took 2 to 4 seconds.

The first run of a pull request downloads the gitleaks archive and saves it in the cache of the pull request. The later runs of the same pull request restore the archive from that cache.

## Making the check required

The check blocks no merge until the branch ruleset of the repository lists it as a required status check. Its name follows the calling job, such as `WF / Secret Scan` for the `Delivery - PR Chores` workflow that `Jahia/.github` manages.

## Limits

- The action detects a secret after the push, when a public repository has already published it. Only GitHub push protection blocks the push itself.
- A branch that is pushed without a pull request is not scanned.
- A pull request can still change the workflows of its own repository, and remove or replace the check that way. A required workflow in an organization ruleset closes that gap, because the pull request cannot change the workflow it names.
- The pinned gitleaks archive runs on `x86_64` runners only.
