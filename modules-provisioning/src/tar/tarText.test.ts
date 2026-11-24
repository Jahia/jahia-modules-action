import {expect, test} from 'vitest'
import {tarText} from './tarText.js'

test('stops at the first NUL', () => {
  expect(tarText(Uint8Array.from([97, 98, 0, 99, 0]))).toBe('ab')
  expect(tarText(Uint8Array.from([97, 98]))).toBe('ab')
})
