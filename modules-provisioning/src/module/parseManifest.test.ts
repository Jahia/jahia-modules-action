import {expect, test} from 'vitest'
import {parseManifest} from './parseManifest.js'

test('joins continuation lines and ignores what is not an attribute', () => {
  const manifest = parseManifest(
    'Manifest-Version: 1.0\r\nJahia-Depends: default,graphql-dxm-pro\r\n vider=[3.0,4),tags\r\n\r\nnot an attribute\r\nUrl: https://a/b\r\n'
  )
  expect(manifest).toEqual({
    'Manifest-Version': '1.0',
    'Jahia-Depends': 'default,graphql-dxm-provider=[3.0,4),tags',
    Url: 'https://a/b'
  })
})
