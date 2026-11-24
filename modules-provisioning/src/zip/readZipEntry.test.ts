import {zipSync} from 'fflate'
import {expect, test} from 'vitest'
import {remoteFileOf} from '../testing/remoteFileOf.js'
import {readZipEntry} from './readZipEntry.js'

const text = (bytes: Uint8Array | undefined) => new TextDecoder().decode(bytes)

test('reads a deflated and a stored entry', async () => {
  const zip = zipSync({
    'deflated.txt': [new TextEncoder().encode('hello '.repeat(50)), {level: 9}],
    'stored.txt': [new TextEncoder().encode('as is'), {level: 0}]
  })
  expect(text(await readZipEntry(remoteFileOf(zip), 'deflated.txt'))).toBe('hello '.repeat(50))
  expect(text(await readZipEntry(remoteFileOf(zip), 'stored.txt'))).toBe('as is')
  expect(await readZipEntry(remoteFileOf(zip), 'absent.txt')).toBeUndefined()
})

test('reads one entry of a large zip without the rest of it', async () => {
  const noise = Uint8Array.from({length: 300_000}, (_, index) => (index * 7919) % 251)
  const zip = zipSync({
    'big.bin': [noise, {level: 0}],
    'META-INF/MANIFEST.MF': new TextEncoder().encode('A: b')
  })
  const file = remoteFileOf(zip)
  expect(text(await readZipEntry(file, 'META-INF/MANIFEST.MF'))).toBe('A: b')
  expect(file.asked()).toBeLessThan(80_000)
})

test('reads a central directory that the tail of the file does not hold', async () => {
  const entries = Object.fromEntries(
    Array.from({length: 2500}, (_, index) => [
      `org/jahia/modules/some/long/package/Class${index}.class`,
      new Uint8Array(1)
    ])
  )
  const zip = zipSync({...entries, 'last.txt': new TextEncoder().encode('found')})
  expect(text(await readZipEntry(remoteFileOf(zip), 'last.txt'))).toBe('found')
})
