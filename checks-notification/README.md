# checks-notification

The action sends the result of a completed run on a pull request to the person who triggered the run, in a
direct message of a Slack app. The code imports the standard library alone, and runs on the `python3` and the
`gh` of the runner.

## Usage

A repository adds a workflow that runs when its checks complete, and names those workflows under
`workflow_run`:

```yaml
name: Checks notification

on:
  workflow_run:
    workflows: [On Code Change (PR)]
    types: [completed]

permissions:
  actions: read
  checks: read
  contents: read
  pull-requests: read

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: jahia/jahia-modules-action/checks-notification@v2
        with:
          slack-token: ${{ secrets.CORTEX_SLACK_BOT_TOKEN }}
          run-id: ${{ github.event.workflow_run.id }}
```

GitHub runs a `workflow_run` workflow from its file on the default branch alone, so the notification starts
once that file merges. The job checks out no code, so the code of a pull request never runs beside the token.
An owner of the organization shares the secret of the Slack app with each repository that calls the action.

## Inputs

| Input | Required | What it holds |
|---|---|---|
| `slack-token` | yes | The bot token of the Slack app. |
| `run-id` | yes | The ID of the completed run, such as `github.event.workflow_run.id`. |
| `github-token` | no | The token that reads the run, its jobs and the commits of its pull request. It defaults to `github.token`, which needs the permissions `actions: read`, `checks: read`, `contents: read` and `pull-requests: read`. |

The Slack app needs the bot scopes `chat:write`, `users:read` and `users:read.email` under **OAuth &
Permissions**, and the **Messages Tab** under **App Home**, where the person reads the message.

## Who receives the message

The action posts to the person who triggered the run, by a push or by a new run of the checks. A run that is
no completed run of a pull request posts nothing, and the run states a notice: a run of a push, a run of a
fork, which names no pull request, and a run that was cancelled, skipped or did not finish. A caller may
therefore run the action on every completed run of its checks. A run that GitHub runs again posts again.

The profile email of a GitHub account is private, so the action reads the email of the last commit of the
pull request that GitHub links to that person, as its author or its committer. `users.lookupByEmail` finds
the Slack member by that email, and `chat.postMessage` posts to that member. A person with no commit in the
pull request, or an email that Slack does not know, gets no message, and the run states a warning. A refusal
of Slack fails the run, and the log names its error code.

## The message

The action posts one message for each run, in one of three states, and the graver the state, the longer the
message. The three share one skeleton: a bar in the color of the state, the header `CI checks passed` or
`CI checks failed`, the pull request and its title, and a line that names the branch, the commit, the
workflow, the attempt and the duration. A gauge of Slack squares follows, at the size of small text, with
one square for each job: green when it passed, yellow when it passed only after a retry, and red when it
failed. The count of the jobs sits right below it, in bold.

| State | Bar | Header | When | What the message adds |
|---|---|---|---|---|
| Passed | `#2EB67D` | `:white_check_mark:` | The run passed, and no job failed in the previous attempt. | Nothing: the link of the pull request is enough. |
| Passed after a retry | `#ECB22E` | `:warning:` | The run passed, and a job that failed in the previous attempt passed in this one. | Each flaky job with the step that failed, and a button that opens the run. |
| Failed | `#E01E5A` | `:x:` | The run failed. | The first failed job with its first error and its place, the buttons **View logs**, **View run** and **Open PR**, and a reply in the thread that details every failed job. |

A failed job with no error of its own beside one that has errors is a gate. The count states it, and the
message shows the job with errors first. Two equal errors, such as the subtests of one test, show once with
their count, such as `×2`.

The errors come from the annotations of the failed jobs, with the file and the line of each one. A title
loses the groups in parentheses that end it, such as the dotted path and the subtest of a unittest failure.
When no failed job wrote an annotation, such as in a Maven build, the read takes the end of the log of each
failed job instead: the `[ERROR]` lines of the last Maven summary, or the last ten lines of another log. A
gate writes no annotation, so a run whose other jobs wrote annotations reads no log.

## The code

- `src/checks_notification.py` runs `notify`, which takes the repository and the Slack client. `notify` finds
  the person who triggered the run, and posts the message of the run to them.
- `src/checks_run.py` reads the run into a `CiChecks`, the data of a completed run of the checks.
- `src/ci_checks.py` turns a `CiChecks` into a `SlackMessage`, and builds its blocks.
- `src/slack.py` holds `SlackMessage` and `SlackClient`, which finds the member and posts the message and its
  thread.
- `src/github_api.py` reads GitHub through `gh api`, and runs a failed read again.
- `tests/` holds the unittest suite, which `.github/workflows/test-checks-notification.yml` runs on each
  pull request that changes the action. `tests/fakes.py` holds the repository and the Slack workspace that a
  test passes in place of the real ones.
