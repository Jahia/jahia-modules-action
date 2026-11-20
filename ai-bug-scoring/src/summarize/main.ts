import { appendFileSync, readFileSync, writeFileSync } from 'node:fs'
import { compact } from './compact'
import { traceRun } from './traceRun'

// summarize-run entry point: prints the deterministic trace of one headless Claude Code run from
// its stream-json output, writes the final result event next to the stream file, and appends one
// row to the step summary. It always exits 0 — reporting must not mask the agent's own exit code.
const run = (): void => {
  const [streamPath = '', key = '', exitCode = ''] = process.argv.slice(2)

  const events: Record<string, unknown>[] = []
  try {
    for (const line of readFileSync(streamPath, 'utf8').split('\n')) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        events.push(JSON.parse(trimmed) as Record<string, unknown>)
      } catch {
        console.log(`[warn] unparseable stream line: ${compact(trimmed, 120)}`)
      }
    }
  } catch (error) {
    console.log(`[warn] could not read stream file: ${String(error)}`)
  }

  const trace = traceRun(events, key, exitCode)
  for (const line of trace.lines) console.log(line)
  if (trace.result !== null) {
    writeFileSync(
      streamPath.replace('.stream.jsonl', '.result.json'),
      JSON.stringify(trace.result, null, 2),
    )
  }
  const summaryPath = process.env.GITHUB_STEP_SUMMARY
  if (summaryPath) {
    appendFileSync(
      summaryPath,
      `| ${key} | ${trace.outcome} | ${trace.turns} | ${trace.duration} | ${trace.cost} | ${exitCode} |\n`,
    )
  }
}

run()
