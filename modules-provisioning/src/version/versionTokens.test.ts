import {expect, test} from 'vitest'
import {versionTokens} from './versionTokens.js'

test('splits numbers and qualifiers', () => {
  expect(versionTokens('4.21.0-jahia8-8')).toEqual([4, 21, 0, 'jahia', 8, 8])
  expect(versionTokens('8.2.3.0-SNAPSHOT')).toEqual([8, 2, 3, 0, 'snapshot'])
  expect(versionTokens('')).toEqual([])
})
