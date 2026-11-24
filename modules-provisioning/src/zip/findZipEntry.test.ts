import {zipSync} from 'fflate'
import {expect, test} from 'vitest'
import {findEndOfCentralDirectory} from './findEndOfCentralDirectory.js'
import {findZipEntry} from './findZipEntry.js'

const zip = zipSync({'a.txt': new Uint8Array([1, 2, 3]), 'dir/b.txt': new Uint8Array(500).fill(9)})
const end = findEndOfCentralDirectory(zip)
const directory = zip.subarray(end.offset, end.offset + end.size)

test('finds an entry by its name', () => {
  expect(findZipEntry(directory, 'a.txt')).toMatchObject({name: 'a.txt', localHeaderOffset: 0})
  const second = findZipEntry(directory, 'dir/b.txt')
  expect(second?.method).toBe(8)
  expect(second?.compressedSize).toBeLessThan(500)
})

test('is undefined for a name the zip does not hold', () => {
  expect(findZipEntry(directory, 'b.txt')).toBeUndefined()
  expect(findZipEntry(new Uint8Array(), 'a.txt')).toBeUndefined()
})
