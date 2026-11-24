import {expect, test} from 'vitest'
import {ENTERPRISE_REPOSITORY, PUBLIC_REPOSITORY} from './constants.js'
import {repositories} from './repositories.js'

test('reads the enterprise group only with an account', () => {
  expect(repositories('ci', 'pw')).toEqual([ENTERPRISE_REPOSITORY, PUBLIC_REPOSITORY])
  expect(repositories('ci', '')).toEqual([PUBLIC_REPOSITORY])
  expect(repositories('', '')).toEqual([PUBLIC_REPOSITORY])
})
