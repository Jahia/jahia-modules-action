import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {fetchText} from './fetchText.js'

test('reads the text, or undefined', async () => {
  const http = fakeHttp({'https://a/x': 'hello'})
  expect(await fetchText(http, ['https://a'], 'x')).toBe('hello')
  expect(await fetchText(http, ['https://a'], 'y')).toBeUndefined()
})
