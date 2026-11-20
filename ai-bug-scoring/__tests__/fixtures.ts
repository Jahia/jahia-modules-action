import type { Bug, Factors } from '../src/types'

export const FIELD_ID = 50177867
export const MARKER = '<!-- ai-bug-scoring -->'

export const bug = (number: number): Bug => ({
  key: `Jahia-example-${String(number)}`,
  repository: 'Jahia/example',
  number,
  url: `https://github.com/Jahia/example/issues/${String(number)}`,
  field_id: FIELD_ID,
})

export const factors = (over: Partial<Factors> = {}): Factors => ({
  ref: 'Jahia/example#1',
  security: false,
  impact: 'editorBlocked',
  feature: 'jContent paste',
  reach: 'high',
  workaround: 'painful',
  regression: true,
  clear: true,
  cloud: false,
  older_version_only: false,
  customers: 1,
  confidence: 'high',
  why: 'Editors cannot paste into a named area of a page.',
  ...over,
})
