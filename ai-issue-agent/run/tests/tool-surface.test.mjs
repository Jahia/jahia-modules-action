import assert from 'node:assert/strict'
import { test } from 'node:test'

import { renderToolSurface } from '../src/tool-surface.mjs'

const surface = renderToolSurface('Read,Write,Bash(ls:*),Bash(cat:*)', 'Bash(git push --force*)')

test('the surface lists the allowed shell commands and the denied ones', () => {
  assert.match(surface, /- `ls`/)
  assert.match(surface, /git push --force/)
})

test('the surface says that a refused chain does not name the failing command', () => {
  assert.match(surface, /refused chain does not name the command that failed/)
})

test('the surface tells the agent to write files with the Write tool, never a redirect', () => {
  assert.match(surface, /redirect is always refused/)
  assert.match(surface, /Write or Edit tool/)
  assert.match(surface, /--body-file/)
})
