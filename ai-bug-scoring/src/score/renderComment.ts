import type { Factors, ScoreRow } from '../types'

const signed = (points: number): string => (points > 0 ? `+${String(points)}` : String(points))

// The breakdown comment posted on the ticket.
export const renderComment = ({
  marker,
  points,
  rows,
  factors,
  agent,
  runUrl,
  date,
}: {
  marker: string
  points: number
  rows: ScoreRow[]
  factors: Factors
  agent: string
  runUrl: string
  date: string
}): string => {
  const lines = [
    marker,
    '> [!NOTE]',
    `> **🤖 PM score: ${String(points)}** · system A2 · ${date} · *a suggestion for the PM decision*`,
    '',
  ]
  lines.push('| Factor | Value | Points |', '|---|---|---|')
  for (const row of rows) {
    lines.push(`| ${row.name} | ${row.text} | ${signed(row.points)} |`)
  }
  lines.push(`| **Total** | | **${String(points)}** |`, '')
  lines.push(`**Why:** ${factors.why}`, '')
  if (factors.confidence === 'low') {
    lines.push('The agent was not sure about the impact: please check it.', '')
  }
  lines.push(
    `<sub>Scored by ${agent} · [run](${runUrl}). A wrong factor? Fix the field value by hand: the job never overwrites a value.</sub>`,
  )
  return lines.join('\n') + '\n'
}
