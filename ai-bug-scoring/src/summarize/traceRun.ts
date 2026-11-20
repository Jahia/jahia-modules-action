import { compact } from './compact'

type StreamEvent = Record<string, unknown>

export interface RunTrace {
  lines: string[]
  result: StreamEvent | null
  outcome: string
  turns: string
  duration: string
  cost: string
}

const contentBlocks = (event: StreamEvent): Record<string, unknown>[] => {
  const message = event.message as { content?: unknown } | undefined
  return Array.isArray(message?.content) ? (message.content as Record<string, unknown>[]) : []
}

// A deterministic trace of everything the agent did (tool calls, messages, final result), and
// the figures of the summary row.
export const traceRun = (events: StreamEvent[], key: string, exitCode: string): RunTrace => {
  const lines = [`--- Agent trace (${key}) ---`]
  let result: StreamEvent | null = null
  for (const event of events) {
    if (event.type === 'system' && event.subtype === 'init') {
      lines.push(`[init] model=${String(event.model)} cwd=${String(event.cwd)}`)
    } else if (event.type === 'assistant') {
      for (const block of contentBlocks(event)) {
        if (block.type === 'text') lines.push(`[say ] ${compact(block.text ?? '')}`)
        else if (block.type === 'tool_use') {
          lines.push(`[tool] ${String(block.name)} ${compact(block.input ?? {})}`)
        }
      }
    } else if (event.type === 'result') {
      result = event
    }
  }
  if (result === null) {
    lines.push(`[end ] no result event found, agent exit code ${exitCode}`)
    return {
      lines,
      result,
      outcome: 'no result (crash/kill)',
      turns: 'n/a',
      duration: 'n/a',
      cost: 'n/a',
    }
  }
  let outcome = typeof result.subtype === 'string' ? result.subtype : 'unknown'
  if (result.is_error === true) outcome = `error (${outcome})`
  const turns = typeof result.num_turns === 'number' ? String(result.num_turns) : 'n/a'
  const duration =
    typeof result.duration_ms === 'number'
      ? `${String(Math.round(result.duration_ms / 1000))}s`
      : 'n/a'
  const cost = typeof result.total_cost_usd === 'number' ? result.total_cost_usd.toFixed(4) : 'n/a'
  lines.push(`[end ] ${outcome} turns=${turns} duration=${duration} cost=$${cost} exit=${exitCode}`)
  lines.push(`[result] ${compact(result.result ?? '', 2000)}`)
  return { lines, result, outcome, turns, duration, cost }
}
