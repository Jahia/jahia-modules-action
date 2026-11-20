import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Bug, BugResult, Octokit, Ticket } from '../types'
import { evaluateBug } from './evaluateBug'
import { setField } from './setField'
import { upsertComment } from './upsertComment'

const loadJson = (path: string): unknown => {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch (error) {
    return error instanceof Error ? error : new Error(String(error))
  }
}

export interface ApplyConfig {
  logDir: string
  dryRun: boolean
  marker: string
  agent: string
  runUrl: string
  date: string
  warn: (message: string) => void
}

// Score each selected bug from its factors file, then write the PM Score field and the comment.
// A bug with no valid factors gets nothing, so its field stays empty and the next run tries it
// again. The comment goes before the field, so a failed field write leaves the bug eligible, and
// the next run edits the same comment instead of posting a second one.
export const applyScores = async (
  { comments, fields }: { comments: Octokit; fields: Octokit },
  config: ApplyConfig,
): Promise<BugResult[]> => {
  const bugs = JSON.parse(readFileSync(join(config.logDir, 'selected-bugs.json'), 'utf8')) as Bug[]
  mkdirSync(join(config.logDir, 'comments'), { recursive: true })
  const results: BugResult[] = []
  for (const bug of bugs) {
    const ticket = loadJson(join(config.logDir, 'tickets', `${bug.key}.json`)) as Ticket | Error
    const factors = loadJson(join(config.logDir, 'factors', `${bug.key}.json`))
    const result = evaluateBug(bug, ticket, factors, config)
    if (result.outcome === 'skipped') {
      config.warn(
        `${result.ref}: ${result.reason ?? ''}. Its field stays empty, so the next run tries it again`,
      )
    } else if (!config.dryRun) {
      try {
        if (result.outcome === 'scored' && result.comment !== undefined) {
          result.comment_action = await upsertComment(comments, bug, result.comment, config.marker)
        }
        await setField(fields, bug, result.value ?? 0)
        result.written = true
      } catch (error) {
        result.outcome = 'write failed'
        result.reason = String(error).slice(0, 200)
        config.warn(`${result.ref}: a write failed (${result.reason}). The next run tries it again`)
      }
    } else if (result.outcome === 'scored' && result.comment !== undefined) {
      writeFileSync(join(config.logDir, 'comments', `${bug.key}.comment.md`), result.comment)
    }
    results.push(result)
  }
  writeFileSync(join(config.logDir, 'results.json'), JSON.stringify(results, null, 2))
  return results
}
