import {expect, test} from 'vitest'
import {compareVersions} from './compareVersions.js'

test.each([
  ['3.10.0', '3.4.0', 1],
  ['3.4', '3.4.0', 0],
  ['8.2.3.0-SNAPSHOT', '8.2.3.0', -1],
  ['4.21.0-jahia8-8', '4.21.0-jahia8-7', 1],
  ['1.0.1', '1.0.0-beta-1', 1],
  ['1.0.0', '1.0.0-beta-1', 1],
  ['2.2.0', '2.4.0', -1],
  ['8.2.0.1', '8.2.0', 1]
])('%s against %s', (left, right, expected) => {
  expect(compareVersions(left, right)).toBe(expected)
  expect(compareVersions(right, left)).toBe(-expected || 0)
})
