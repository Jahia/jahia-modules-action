import type { BugResult } from '../types'

const row = (result: BugResult): string => {
  const value = result.value === undefined ? '' : String(result.value)
  const detail =
    result.reason ?? [result.impact, result.reach].filter((part) => part !== undefined).join(' / ')
  const outcome = result.outcome + (result.written ? ', written' : '')
  return `| [${result.ref}](${result.url}) | ${value} | ${detail} | ${outcome} |`
}

// The job-summary table: one row per bug, written or not.
export const renderScoreSummary = (results: BugResult[], writing: boolean): string =>
  `### PM scores (${writing ? 'written' : 'dry run, nothing written'})\n\n` +
  '| Bug | Field value | Impact / reach, or reason | Outcome |\n' +
  '|---|---|---|---|\n' +
  results.map((result) => row(result) + '\n').join('')
