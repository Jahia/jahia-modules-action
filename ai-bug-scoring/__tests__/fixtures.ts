import type { Bug } from '../src/types'

export const FIELD_ID = 50177867
export const MARKER = '<!-- ai-bug-scoring -->'

export const bug = (number: number): Bug => ({
  key: `Jahia-example-${String(number)}`,
  repository: 'Jahia/example',
  number,
  url: `https://github.com/Jahia/example/issues/${String(number)}`,
  field_id: FIELD_ID,
})
