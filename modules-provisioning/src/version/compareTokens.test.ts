import {expect, test} from 'vitest'
import {compareTokens} from './compareTokens.js'

test.each([
  [1, 1, 0],
  [2, 10, -1],
  [10, 2, 1],
  [undefined, 0, 0],
  [undefined, 1, -1],
  [1, undefined, 1],
  ['beta', 'rc', -1],
  ['rc', 'beta', 1],
  ['beta', 1, -1],
  [1, 'beta', 1],
  ['snapshot', undefined, -1],
  [undefined, 'snapshot', 1],
  [undefined, undefined, 0]
])('compares %s with %s', (left, right, expected) => {
  expect(compareTokens(left, right)).toBe(expected)
})
