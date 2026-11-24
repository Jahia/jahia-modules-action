import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {fetchFirst} from './fetchFirst.js'

test('answers from the first repository that serves the path', async () => {
  const http = fakeHttp({'https://a/x': {status: 401}, 'https://b/x': 'from b', 'https://c/x': 'from c'})
  const response = await fetchFirst(http, ['https://a', 'https://b', 'https://c'], 'x')
  expect(await response?.text()).toBe('from b')
  expect(http.calls).toEqual(['https://a/x', 'https://b/x'])
})

test('is undefined when no repository serves the path', async () => {
  expect(await fetchFirst(fakeHttp({}), ['https://a', 'https://b'], 'x')).toBeUndefined()
  expect(await fetchFirst(fakeHttp({}), [], 'x')).toBeUndefined()
})

test('fails on a status that is not an absence', async () => {
  await expect(fetchFirst(fakeHttp({'https://a/x': {status: 400}}), ['https://a'], 'x')).rejects.toThrow(
    'HTTP 400'
  )
})
