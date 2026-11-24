import {expect, test} from 'vitest'
import {splitTopLevel} from './splitTopLevel.js'

test('keeps the comma of a version range', () => {
  expect(splitTopLevel('default, graphql=[3.0,4) ,tags=(1,2],,')).toEqual([
    'default',
    'graphql=[3.0,4)',
    'tags=(1,2]'
  ])
  expect(splitTopLevel('')).toEqual([])
  expect(splitTopLevel('a;b', ';')).toEqual(['a', 'b'])
})
