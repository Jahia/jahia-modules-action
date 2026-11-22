import { renderScoreSummary } from '../src/report/renderScoreSummary'
import { runFailure } from '../src/report/runFailure'
import type { BugResult } from '../src/types'

const scored = (over: Partial<BugResult> = {}): BugResult => ({
  ref: 'Jahia/example#1',
  key: 'Jahia-example-1',
  url: 'https://github.com/Jahia/example/issues/1',
  outcome: 'scored',
  title: 'Editors cannot paste',
  rows: [{ name: 'Impact', text: 'Editors blocked', points: 20 }],
  value: 45,
  points: 45,
  impact: 'editorBlocked',
  reach: 'high',
  written: true,
  ...over,
})

describe('runFailure', () => {
  it('fails a write run that wrote nothing', () => {
    const failure = runFailure([scored({ outcome: 'skipped', written: undefined })], false)
    expect(failure).toContain('no PM Score field was written')
  })

  it('passes a dry run that wrote nothing', () => {
    expect(runFailure([scored({ written: undefined })], true)).toBeNull()
  })

  it('passes a write run with one write', () => {
    expect(
      runFailure([scored(), scored({ outcome: 'skipped', written: undefined })], false),
    ).toBeNull()
  })
})

describe('renderScoreSummary', () => {
  it('renders one row per bug with the factor columns of the first scored bug', () => {
    const summary = renderScoreSummary([scored()], true)
    expect(summary).toContain('### PM scores (written)')
    expect(summary).toContain('| Impact |')
    expect(summary).toContain('[Jahia/example#1](https://github.com/Jahia/example/issues/1)')
  })

  it('escapes a pipe so a title cannot end its cell', () => {
    const summary = renderScoreSummary([scored({ title: 'a | b' })], false)
    expect(summary).toContain('a \\| b')
  })
})
