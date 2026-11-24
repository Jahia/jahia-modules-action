import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {openFirstRemoteFile} from './openFirstRemoteFile.js'

test('opens the first URL that names a file', async () => {
  const http = fakeHttp({'https://b/f': new Uint8Array(7)})
  expect((await openFirstRemoteFile(http, ['https://a/f', 'https://b/f', 'https://c/f']))?.size).toBe(7)
  expect(http.calls).toEqual(['https://a/f', 'https://b/f'])
  expect(await openFirstRemoteFile(http, ['https://a/f'])).toBeUndefined()
  expect(await openFirstRemoteFile(http, [])).toBeUndefined()
})
