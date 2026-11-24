import {expect, test, vi} from 'vitest'
import {NEXUS} from '../constants.js'
import {createHttp} from './createHttp.js'

const answering = (...statuses: number[]) => {
  const fetch = vi.fn<typeof globalThis.fetch>()
  statuses.forEach(status => fetch.mockResolvedValueOnce(new Response(null, {status})))
  return fetch
}
const headersOf = (fetch: ReturnType<typeof answering>, call = 0) =>
  (fetch.mock.calls[call]?.[1]?.headers ?? {}) as Record<string, string>

test('sends the Nexus account to Nexus only', async () => {
  const fetch = answering(200, 200)
  const http = createHttp({fetch, username: 'ci', password: 'pw'})
  await http(`${NEXUS}/groups/public/a.pom`)
  await http('https://store.jahia.com/modules/list.json')
  expect(headersOf(fetch, 0).Authorization).toBe('Basic Y2k6cHc=')
  expect(headersOf(fetch, 1).Authorization).toBeUndefined()
})

test('sends no account when there is none, and keeps the headers of the call', async () => {
  const fetch = answering(206)
  await createHttp({fetch})(`${NEXUS}/a.jar`, {Range: 'bytes=0-0'})
  expect(headersOf(fetch)).toEqual({'User-Agent': 'jahia-modules-provisioning', Range: 'bytes=0-0'})
})

test('encodes the spaces of a Store path once', async () => {
  const fetch = answering(200, 200)
  const http = createHttp({fetch})
  await http('https://store.jahia.com/package/Augmented Search.jar')
  await http('https://store.jahia.com/package/Augmented%20Search.jar')
  expect(fetch.mock.calls.map(call => call[0])).toEqual([
    'https://store.jahia.com/package/Augmented%20Search.jar',
    'https://store.jahia.com/package/Augmented%20Search.jar'
  ])
})

test('tries a server error again, and returns a client error as it is', async () => {
  const wait = vi.fn(async () => {})
  const fetch = answering(503, 404)
  const response = await createHttp({fetch, wait})('https://example.org/a')
  expect(response.status).toBe(404)
  expect(fetch).toHaveBeenCalledTimes(2)
})

test('fails once every attempt met a server error', async () => {
  const fetch = answering(500, 502)
  await expect(
    createHttp({fetch, attempts: 2, wait: async () => {}})('https://example.org/a')
  ).rejects.toThrow('answered HTTP 502')
})

test('waits with a timer by default', async () => {
  vi.useFakeTimers()
  const fetch = answering(500, 200)
  const pending = createHttp({fetch})('https://example.org/a')
  await vi.advanceTimersByTimeAsync(2000)
  expect((await pending).status).toBe(200)
  vi.useRealTimers()
})
