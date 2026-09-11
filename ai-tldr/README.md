# AI TL;DR

Summarizes one issue or pull request into a single short comment, on demand: a human adds the
**`🤖 TL;DR`** label, an agent reads the whole thread and everything it links, and posts one
paragraph plus at most three bullets saying where the thread stands and what happens next. The
label is removed once the comment is posted, so it is always free to request the next one.

The point is compression. These threads run to dozens of comments and several pull requests
across repositories; the summary exists for the person who has to act on one without reading it.

## Flow

```
label added ──▶ check-request (ubuntu-slim, no LLM)
                 │
                 ├─ stale (closed, or label already gone) ──▶ stop, silently
                 ├─ a TL;DR sits in the last 3 comments ───▶ remove the label, say why once, stop
                 └─ a TL;DR is owed
                      │
                      ▼
                    agent job (self-hosted): mTLS tunnel ▸ cortex ▸ Claude Code
                      │
                      ├─ agent writes the comment to a file (it cannot post)
                      ├─ the action posts that file  ─┐
                      └─ the action removes the label ┘ only after a comment exists
```

The refusal explains itself **once**. If the thread's latest comment is already that notice,
a further request just takes the label off in silence — a row of identical cancellations helps
nobody, and it would push the original TL;DR out of the lookback window, which would eventually
let a duplicate summary through.

Two jobs, deliberately. Re-labelling a thread that was just summarized costs one `ubuntu-slim`
job, not an agent run — and that refusal is the common case once people start using the label.

## What is deterministic, and why

The agent never reaches GitHub's write surface. It writes a markdown file; posting the file,
removing the label, and refusing a too-soon request are all plain action steps. So "whether a
comment was posted" and "whether the label came off" never depend on the model doing as it was
told — only "what the comment says" does.

Failure leaves the label **on**. That is the retry handle: re-run the job, or take the label off
and put it back.

## Requirements

Same as [`ai-pr-review`](../ai-pr-review/README.md): the caller needs `id-token: write` for the
mTLS tunnel, the organization variables `AI_LITELLM_*` / `INFRAJAHIA_MTLS_*`, and the secrets
`AI_LITELLM_AUTH_TOKEN`, `AI_AGENT_GH_ISSUES_PRS_CHORES`, `INFRAJAHIA_MTLS_*`,
`BASTION_SSH_PRIVATE_KEY_JAHIACI`.

The repository must carry the label. Create it once per repository:

```bash
gh label create '🤖 TL;DR' --color bff17d --repo Jahia/<repo> \
  --description 'Ask the AI agent for a short summary of this thread'
```

The mTLS broker mints certificates only for allowlisted repositories **and triggering events** —
a repository whose `issues`/`pull_request` label events are not allowlisted will fail at the
tunnel step.

## Inputs

Wired by [`reusable-ai-tldr.yml`](../.github/workflows/reusable-ai-tldr.yml); see that file for
the caller-facing inputs (`lookback`, `post_comment`, `instance_type`, …).

`post_comment: false` is review mode: the agent runs, nothing is posted, the label stays, and the
comment it *would* have posted lands in the job summary and the run artifact. Use it to iterate on
the prompt without writing to a real thread.

## Artifacts

`ai-tldr-logs` holds the prompt, the agent's full stream and rendered transcript, and the comment
file. One day on GitHub, one week on the Jahia servers.
