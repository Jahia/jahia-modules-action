import {expect, test} from 'vitest'
import {basicAuthorization} from './basicAuthorization.js'

test('encodes the account', () => {
  expect(basicAuthorization('ci', 's3cret')).toBe('Basic Y2k6czNjcmV0')
})
