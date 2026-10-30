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

| Input | Required | What it holds |
|---|---|---|
| `slack-token` | yes | The bot token of the Slack app. |
| `github-token` | no | The token that reads the data of the event on GitHub. It defaults to `github.token`. For `ci_checks`, it needs the permissions `actions: read`, `checks: read`, `contents: read` and `pull-requests: read`. |

The action reads the event from the workflow, in `GITHUB_EVENT_NAME` and `GITHUB_EVENT_PATH`, so it takes no
input that names the event.

The Slack app needs the bot scopes `chat:write`, `users:read` and `users:read.email` under **OAuth &
Permissions**, and the **Messages Tab** under **App Home**, where the person reads the message.

## How the action finds the person

The event names the GitHub account of the person and a pull request. The profile email of a GitHub account is
private. The action therefore reads the email of the last commit of the pull request that GitHub links to that
account, as its author or its committer. `users.lookupByEmail` finds the Slack member by that email, and
`chat.postMessage` posts to that member. A person with no commit in the pull request gets no message, and so
does an email that Slack does not know. The run then states a warning. A refusal of Slack or of GitHub fails the
run, and the log names its error.

An event that the action does not know fails the run, and an event with nothing to send states a notice.

## The event `ci_checks`

The message goes to the person who triggered the run, by a push or by a new run of the checks. A run that is no
completed run of a pull request posts nothing, and the run states a notice. Four runs post nothing:

- a run of a push;
- a run of a fork, which names no pull request;
- a run that was cancelled or skipped;
- a run that did not finish.

A caller may therefore run the action on every completed run of its checks. A run that GitHub runs again posts
again.

The action posts one message for each run, in one of three states, and the graver the state, the longer the
message. The three share one skeleton:

- a bar in the color of the state, and the header;
- the repository, then the title of the pull request with its number;
- the state of the pull request in bold behind a circle of its color, its author, its commits and its branches,
  as its page on GitHub shows them;
- the workflow, the commit, the attempt and the duration of the run;
- a gauge of Slack squares, one for each job, with the count of the jobs below it. A square is green when its
  job passed, yellow when it passed only after a retry, and red when it failed.

| State | Bar | Header | When | What the message adds |
|---|---|---|---|---|
| Passed | `#2EB67D` | `:white_check_mark:` | The run passed, and no job failed in the previous attempt. | Nothing: the link of the pull request is enough. |
| Passed after a retry | `#ECB22E` | `:warning:` | The run passed, and a job that failed in the previous attempt passed in this one. | Each flaky job with the step that failed, and a button that opens the run. |
| Failed | `#E01E5A` | `:x:` | The run failed. | The first failed job with its first error and its place, a note for each other failed job, the buttons **View logs** and **View run**, and a reply in the thread that details every failed job. |

A failed job with no error of its own beside one that has errors is a gate. The message shows the job with
errors first, and a note counts the gates. Two equal errors, such as the subtests of one test, show once with
their count, such as `×2`.

The errors come from the annotations of the failed jobs, with the file and the line of each one. A title
loses the groups in parentheses that end it, such as the dotted path and the subtest of a unittest failure.
When no failed job wrote an annotation, such as in a Maven build, the read takes the end of the log of each
failed job instead. It keeps the `[ERROR]` lines of the last Maven summary, or the last three lines of another
log. The log ends at its last error, before the steps that clean up the job. A gate writes no annotation, so a
run whose other jobs wrote annotations reads no log.

## Add an event

1. Create the folder `src/events/<name>/`:
   - `event.py` reads the data of the event from GitHub;
   - `template.py` builds the `SlackMessage` from that data. It calls `compose` of `src/templates/message.py`,
     which opens every message on the header of the event. An event of a pull request adds the part that `show`
     of `src/templates/pull_request.py` builds, then its own blocks from `src/blocks.py`;
   - `__init__.py` holds `read(payload, github)`, which returns the `Notification` of `src/notification.py`, or
     raises `Skip` with the reason to send nothing.
2. Add the GitHub event that triggers it to the table `EVENTS` of `src/events/__init__.py`.
3. Add its tests, `tests/test_<name>_event.py` and `tests/test_<name>_template.py`, and its row and its section
   to this README.

## The code

- `src/main.py` reads the GitHub event, runs `read` of its folder, finds the person and posts the message.
- `src/events/` holds one folder for each event, and the table that maps a GitHub event to its folder.
- `src/notification.py` holds `Notification` and `Skip`, what the folder of an event returns to `main.py`.
- `src/templates/` holds the parts that every template shares. `message.py` opens a message on the header of
  its event. `pull_request.py` shows the repository, the title and the state of a pull request, then a
  separator.
- `src/pull_request.py` reads a pull request, which every event of a pull request shows.
- `src/people.py` finds the email of a GitHub account in the commits of a pull request.
- `src/blocks.py` builds the Block Kit blocks that every template uses, and escapes the markup of Slack.
- `src/slack.py` holds `SlackMessage` and `SlackClient`, which finds the member and posts the message and its
  thread.
- `src/github_api.py` reads GitHub through `gh api`, and runs a failed read again.
- `tests/` holds the unittest suite, which `.github/workflows/test-slack-notification.yml` runs on each pull
  request that changes the action. `tests/fakes.py` holds the repository and the Slack workspace that a test
  passes in place of the real ones.
