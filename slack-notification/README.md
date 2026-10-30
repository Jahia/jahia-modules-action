# slack-notification

The action posts the Slack message of the GitHub event that triggered the workflow, as a direct message of a Slack
app. The message goes to the person the event concerns. Each event that the action knows has a folder under
`src/events/`, which reads the data of the event and builds its message. The code imports the standard library
alone. It runs on the `gh` of the runner and on its `python3`, which must be Python 3.11 or later, as on
`ubuntu-24.04`.

| Event | GitHub event of the workflow | Who receives the message |
|---|---|---|
| [`ci_checks`](#the-event-ci_checks) | `workflow_run`, `completed`, on the workflows of the checks | The person who triggered the run |

## Usage

A repository adds a workflow that runs on the GitHub event of a message. For `ci_checks`, the workflow runs when
the checks complete, and names those workflows under `workflow_run`:

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
      - uses: jahia/jahia-modules-action/slack-notification@v2
        with:
          slack-token: ${{ secrets.CORTEX_SLACK_BOT_TOKEN }}
```

GitHub runs a `workflow_run` workflow from its file on the default branch alone, so the notification starts
once that file merges. The job checks out no code, so the code of a pull request never runs beside the token.
An owner of the organization shares the secret of the Slack app with each repository that calls the action.

## Inputs

| Input | Required | Value |
|---|---|---|
| `slack-token` | yes | The bot token of the Slack app. |
| `github-token` | no | The token that reads the data of the event on GitHub. It defaults to `github.token`. For `ci_checks`, it needs the permissions `actions: read`, `checks: read`, `contents: read` and `pull-requests: read`. |

The action reads the event from the workflow, in `GITHUB_EVENT_NAME` and `GITHUB_EVENT_PATH`, so no input
names the event.

The Slack app needs the bot scopes `chat:write`, `users:read` and `users:read.email` under **OAuth &
Permissions**. It also needs the **Messages Tab** under **App Home**, where the person reads the message.

## How the action finds the person

The event names the GitHub account of the person and a pull request. The profile email of a GitHub account is
private by default. The action therefore reads the emails of the commits of the pull request that GitHub links to
that account, as their author or their committer. It reads the last commit first, and leaves out the address
`users.noreply.github.com` that GitHub gives an account that hides its email.

`users.lookupByEmail` finds the Slack member by the first email that Slack knows, and `chat.postMessage` posts to
that member. A person with no such email gets no message, and so does a person whose emails Slack does not know.
The run then states a warning. A refusal of Slack or of GitHub fails the run, and the log names its error.

An event that the action does not know fails the run, and an event with nothing to send states a notice.

## The event `ci_checks`

The message goes to the person who triggered the run, by a push or by a new run of the checks. A run that is no
completed run of a pull request posts nothing, and the run states a notice. Four runs post nothing:

- a run of a push;
- a run of a fork, which names no pull request;
- a run that was cancelled or skipped;
- a run that did not finish.

A caller may therefore run the action on every completed run of its checks. A run that GitHub runs again posts
again, and each message reads the jobs of the attempt that its event names. GitHub can send the event before each
job carries its conclusion, so the action reads the jobs up to 6 times, 10 seconds apart, until each job carries
one. A job that still has no conclusion after the last read counts neither as passed nor as failed, and the run
states a warning that names it.

The action posts one message for each run, in one of three states, on a bar in the color of its state. The
graver the state, the longer the message. The three share one skeleton:

- the header;
- the repository, then the title of the pull request with its number;
- the state of the pull request in bold behind a circle of its color, its author, its commits and its branches,
  as its page on GitHub shows them, then a separator;
- the workflow, which links to the run, the commit, the attempt and the duration;
- the count of the jobs, which leaves out a job that was skipped or cancelled, such as by fail-fast, and a job with
  no conclusion. A gauge of Slack squares opens that line when a job failed or passed only after a retry, one square
  for each job. A square is green when its job passed, yellow when it passed only after a retry, and red when it
  failed.

Only an attachment of Slack draws the bar. Slack folds a high attachment behind "Show more", so the detail of a
failure or of a retry can sit behind it.

| State | Bar | Header | When | What the message adds |
|---|---|---|---|---|
| Passed | `#2EB67D` | `:white_check_mark:` | The run passed, and no job failed in the previous attempt. | Nothing: the link of the pull request is enough. |
| Passed after a retry | `#ECB22E` | `:warning:` | The run passed, and a job that failed in the previous attempt passed in this one. | Each flaky job with its step in bold and the attempts, and a button that opens the run. |
| Failed | `#E01E5A` | `:x:` | The run failed. | Each failed job with its step in bold, the place of its first error and that error in a block of code, the buttons **View logs** and **View run**, and a reply in the thread that details every error. |

A failed job with no error in its annotations or its log, beside one that has errors, is a gate. The message
shows the jobs with errors first and a gate last, with a blank line between two jobs. Two equal errors, such as
the subtests of one test, show once with their count, such as `×2`.

The errors come from the annotations of each failed job, with the file and the line of each one. A title loses
the groups in parentheses that end it, such as the dotted path and the subtest of a unittest failure. A failed
job with no annotation, such as a Maven build, gives the end of its log instead. The read keeps the output of the
failed step up to its last error, so the setup of the job and its cleanup never show. It keeps the `[ERROR]`
lines of the last Maven summary, or the last three lines of another log.

## Add an event

1. Create the folder `src/events/<name>/`:
   - `event.py` reads the data of the event from GitHub;
   - `template.py` builds the `SlackMessage` from that data. It calls `compose` of `src/templates/message.py`,
     which opens every message on the header of the event. An event of a pull request adds the part that `show`
     of `src/templates/pull_request.py` builds, then its own blocks from `src/blocks.py`;
   - `__init__.py` defines `read(payload, github)`, which returns the `Notification` of `src/notification.py`, or
     raises `Skip` with the reason to send nothing.
2. Add the GitHub event that triggers it to the table `EVENTS` of `src/events/__init__.py`.
3. Add its tests, `tests/test_<name>_event.py` and `tests/test_<name>_template.py`, and its row and its section
   to this README.

## The code

- `src/main.py` reads the GitHub event, runs `read` of its folder, finds the person and posts the message.
- `src/events/` contains one folder for each event, and the table that maps a GitHub event to its folder.
- `src/notification.py` defines `Notification` and `Skip`, what the folder of an event returns to `main.py`.
- `src/templates/` contains the parts that every template shares. `message.py` opens a message on the header of
  its event. `pull_request.py` shows the repository, the title and the state of a pull request, then a
  separator.
- `src/pull_request.py` reads a pull request, which every event of a pull request shows.
- `src/people.py` finds the emails of a GitHub account in the commits of a pull request.
- `src/blocks.py` builds the Block Kit blocks that every template uses: blocks of markdown, which escape the
  markup of Slack, and blocks of rich text.
- `src/slack.py` defines `SlackMessage` and `SlackClient`, which finds the member and posts the message and its
  thread.
- `src/github_api.py` reads GitHub through `gh api`, and runs a failed read again.
- `tests/` contains the unittest suite, which `.github/workflows/test-slack-notification.yml` runs on each pull
  request that changes the action. `tests/fakes.py` defines the repository and the Slack workspace that a test
  passes in place of the real ones.
