import { readFileSync, writeFileSync } from 'node:fs'

// Collect every call the permission layer refused, from one run's stream-json. This is a
// deterministic pass over the stream, not something the agent reports about itself: an
// agent that has just been refused is the least reliable witness to what it was refused.
// The point is the next allowlist — a refusal recurring across runs is a tool the duty
// needs and does not have.
export const tallyDeniedCalls = ({ streamFile, outputFile, label }) => {
  let lines = []
  try {
    lines = readFileSync(streamFile, 'utf8').split('\n')
  } catch {
    writeFileSync(outputFile, `# Denied calls — ${label}\n\nNo stream file was produced.\n`)
    return 0
  }

  // tool_use_id -> what the call was doing: a permission_denied event names the tool and
  // the reason, never the call, and "Bash was denied" is useless next to the command.
  const calls = new Map()
  const denials = []
  for (const line of lines) {
    if (!line.trim()) continue
    let event
    try {
      event = JSON.parse(line)
    } catch {
      continue
    }
    if (event?.type === 'assistant') {
      for (const block of event.message?.content ?? []) {
        if (block?.type === 'tool_use' && block.id) {
          const input = block.input ?? {}
          const detail = typeof input.command === 'string' ? input.command : JSON.stringify(input)
          calls.set(block.id, { tool: block.name ?? '?', detail: detail.replace(/\s+/g, ' ').trim() })
        }
      }
    } else if (event?.type === 'system' && event.subtype === 'permission_denied') {
      const call = calls.get(event.tool_use_id) ?? { tool: event.tool_name ?? '?', detail: '' }
      denials.push({ ...call, reason: event.decision_reason_type ?? 'unknown' })
    }
  }

  const body = [`# Denied calls — ${label}`, '']
  if (denials.length) {
    body.push('| Tool | Call | Reason |', '|---|---|---|')
    body.push(
      ...denials.map(
        ({ tool, detail, reason }) =>
          `| ${tool} | \`${detail.replaceAll('`', "'").slice(0, 200) || '(no detail)'}\` | ${reason} |`,
      ),
    )
  } else {
    body.push('No call was denied during this run.')
  }
  writeFileSync(outputFile, `${body.join('\n')}\n`)
  return denials.length
}
