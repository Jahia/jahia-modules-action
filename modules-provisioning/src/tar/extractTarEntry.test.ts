import {expect, test} from 'vitest'
import {tarOf} from '../testing/tarOf.js'
import {extractTarEntry} from './extractTarEntry.js'

const text = (bytes: Uint8Array | undefined) =>
  bytes === undefined ? undefined : new TextDecoder().decode(bytes)

test('extracts the entry the predicate accepts', () => {
  const tar = tarOf([
    ['package/README.md', 'x'.repeat(700)],
    ['package/empty', ''],
    ['package/package.json', '{"name":"a"}']
  ])
  expect(text(extractTarEntry(tar, name => name === 'package/package.json'))).toBe('{"name":"a"}')
  expect(text(extractTarEntry(tar, name => name === 'package/README.md'))).toBe('x'.repeat(700))
  expect(extractTarEntry(tar, name => name === 'absent')).toBeUndefined()
})

test('joins the prefix of a long name', () => {
  const tar = tarOf([['package.json', '{}', 'package']])
  expect(text(extractTarEntry(tar, name => name === 'package/package.json'))).toBe('{}')
})

test('is undefined for an empty archive', () => {
  expect(extractTarEntry(new Uint8Array(), () => true)).toBeUndefined()
})
