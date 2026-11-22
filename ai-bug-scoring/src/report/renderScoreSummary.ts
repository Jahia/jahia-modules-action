import type { BugResult } from '../types'

// A pipe in a title or a value would end its table cell.
const cell = (text: string): string => text.replace(/\|/g, '\\|')

const row = (result: BugResult, factorNames: string[]): string => {
  const value = result.value === undefined ? '' : String(result.value)
  const detail =
    result.reason ?? [result.impact, result.reach].filter((part) => part !== undefined).join(' / ')
  const outcome = result.outcome + (result.written ? ', written' : '')
  const answers = factorNames.map(
    (name) => result.rows?.find((factor) => factor.name === name)?.text ?? '',
  )
  const cells = [
    `[${result.ref}](${result.url})`,
    cell(result.title ?? ''),
    value,
    detail,
    outcome,
    ...answers.map(cell),
  ]
  return `| ${cells.join(' | ')} |`
}

// The job-summary table: one row per bug, written or not, then one column per factor with the
// answer of the agent. The factor columns follow the breakdown of the first scored bug.
export const renderScoreSummary = (results: BugResult[], writing: boolean): string => {
  const factorNames =
    results.find((result) => result.rows)?.rows?.map((factor) => factor.name) ?? []
  const header = [
    'Bug',
    'Title',
    'Field value',
    'Impact / reach, or reason',
    'Outcome',
    ...factorNames,
  ]
  return (
    `### PM scores (${writing ? 'written' : 'dry run, nothing written'})\n\n` +
    `| ${header.join(' | ')} |\n` +
    `|${header.map(() => '---').join('|')}|\n` +
    results.map((result) => row(result, factorNames) + '\n').join('')
  )
}
