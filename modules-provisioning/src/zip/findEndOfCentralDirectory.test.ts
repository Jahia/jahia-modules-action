import {zipSync} from 'fflate'
import {expect, test} from 'vitest'
import {findEndOfCentralDirectory} from './findEndOfCentralDirectory.js'

test('finds the central directory of a zip', () => {
  const zip = zipSync({'a.txt': new Uint8Array([1, 2, 3])}, {level: 0})
  const end = findEndOfCentralDirectory(zip)
  expect(end.offset + end.size).toBe(zip.length - 22)
  expect(new DataView(zip.buffer).getUint32(end.offset, true)).toBe(0x02014b50)
})

test('refuses bytes that are not a zip', () => {
  expect(() => findEndOfCentralDirectory(new Uint8Array(100))).toThrow('not a zip')
  expect(() => findEndOfCentralDirectory(new Uint8Array(3))).toThrow('not a zip')
})
