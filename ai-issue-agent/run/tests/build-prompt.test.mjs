import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'

import { buildPrompt } from '../src/build-prompt.mjs'

// Render a template with the given inputs and return the prompt that was written.
const render = (template, inputs) => {
  const dir = mkdtempSync(join(tmpdir(), 'build-prompt-'))
  const templatePath = join(dir, 'prompt.md')
  const outputPath = join(dir, 'out.md')
  writeFileSync(templatePath, template)
  buildPrompt({ templatePath, outputPath, ...inputs })
  return readFileSync(outputPath, 'utf8')
}

test('substitutes every occurrence of a placeholder', () => {
  const prompt = render('__A__ and __A__ and __B__', { replacements: { A: 'one', B: 'two' } })
  assert.equal(prompt, 'one and one and two')
})

test('throws on a placeholder that nothing replaces', () => {
  assert.throws(
    () => render('Hello __NAME__', { replacements: {} }),
    /prompt template placeholder not replaced: __NAME__/,
  )
})

test('keeps $ patterns of a replacement value as written', () => {
  const prompt = render('cost: __PRICE__', { replacements: { PRICE: "$& $1 $$ $'" } })
  assert.equal(prompt, "cost: $& $1 $$ $'")
})

test('substitutes a literal value, and keeps $ patterns in it as written', () => {
  const prompt = render('request: __REQUEST__', { replacements: {}, literal: { REQUEST: 'pay $& now' } })
  assert.equal(prompt, 'request: pay $& now')
})

test('does not scan a literal value for placeholders', () => {
  // A dispatcher who types __UNKNOWN__ in the request must neither crash the build nor
  // trigger a second substitution.
  const prompt = render('request: __REQUEST__ / tail: __TAIL__', {
    replacements: { TAIL: 'end' },
    literal: { REQUEST: 'mentions __TAIL__ and __UNKNOWN__' },
  })
  assert.equal(prompt, 'request: mentions __TAIL__ and __UNKNOWN__ / tail: end')
})

test('still throws on an unreplaced placeholder when a literal is given', () => {
  assert.throws(
    () => render('__REQUEST__ and __MISSING__', { replacements: {}, literal: { REQUEST: 'x' } }),
    /placeholder not replaced: __MISSING__/,
  )
})

test('a literal key absent from the template is ignored', () => {
  const prompt = render('no placeholder here', { replacements: {}, literal: { REQUEST: 'x' } })
  assert.equal(prompt, 'no placeholder here')
})

test('works without a literal, as before the dispatch change', () => {
  const prompt = render('__X__', { replacements: { X: 1 } })
  assert.equal(prompt, '1')
})
