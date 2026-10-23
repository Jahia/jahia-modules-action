// Two markers, two jobs: STATUS_MARKER is the comment's identity (how every run finds it
// again, so it never changes), STATE_MARKER_OPEN/CLOSE delimit the machine-readable state
// rewritten on every state change. README.md documents the full format.
export const STATUS_MARKER = '<!-- cortex-issue-agent-status -->'
export const STATE_MARKER_OPEN = '<!-- cortex-issue-agent-state'
export const STATE_MARKER_CLOSE = '-->'
