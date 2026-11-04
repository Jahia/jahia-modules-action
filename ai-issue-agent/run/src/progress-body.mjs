// The body of the task comment with the sidecar's progress lines in it. The stats sit between
// the progress marker and the footer marker that cortex's tools/jahia-issue-agent writes before
// the footer (Claude Code version, model, run link), so the footer stays the last line. A body
// without the footer marker, from an older cortex, takes the stats at its end.
export const PROGRESS_MARKER = '<!-- cortex-issue-agent-progress -->'
export const FOOTER_MARKER = '<!-- cortex-issue-agent-footer -->'

export function withProgress(body, stats) {
  const footerAt = body.indexOf(FOOTER_MARKER)
  const footer = footerAt === -1 ? '' : body.slice(footerAt)
  const content = (footerAt === -1 ? body : body.slice(0, footerAt)).split(PROGRESS_MARKER)[0].trimEnd()
  const progress = `${content}\n\n${PROGRESS_MARKER}\n${stats}`
  return footer ? `${progress}\n\n${footer}` : progress
}
