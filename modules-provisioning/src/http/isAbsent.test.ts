import {expect, test} from 'vitest'
import {isAbsent} from './isAbsent.js'

test.each([
  [401, true],
  [403, true],
  [404, true],
  [200, false],
  [500, false]
])('HTTP %i', (status, expected) => {
  expect(isAbsent(new Response(null, {status}))).toBe(expected)
})
