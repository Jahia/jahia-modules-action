import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {openRemoteFile} from './openRemoteFile.js'

const bytes = Uint8Array.from({length: 100}, (_, index) => index)

test('reads ranges of a file that serves them', async () => {
  const http = fakeHttp({'https://a/f': bytes})
  const file = await openRemoteFile(http, 'https://a/f')
  expect(file?.size).toBe(100)
  expect([...(await file!.read(10, 13))]).toEqual([10, 11, 12])
  expect((await file!.read(5, 5)).length).toBe(0)
  expect(http.calls.length).toBe(2)
})

test('keeps the whole file of a server that ignores ranges', async () => {
  const http = fakeHttp({'https://a/f': {noRanges: bytes}})
  const file = await openRemoteFile(http, 'https://a/f')
  expect(file?.size).toBe(100)
  expect([...(await file!.read(98, 100))]).toEqual([98, 99])
  expect(http.calls.length).toBe(1)
})

test('is undefined for a file the server does not have', async () => {
  expect(await openRemoteFile(fakeHttp({}), 'https://a/f')).toBeUndefined()
})

test('fails on an answer that is neither a file nor a range', async () => {
  await expect(openRemoteFile(fakeHttp({'https://a/f': {status: 400}}), 'https://a/f')).rejects.toThrow(
    'serves no byte range'
  )
  await expect(openRemoteFile(async () => new Response(null, {status: 206}), 'https://a/f')).rejects.toThrow(
    'serves no byte range'
  )
})

test('fails when a later range is refused', async () => {
  const answers = [
    new Response(null, {status: 206, headers: {'Content-Range': 'bytes 0-0/100'}}),
    new Response(null, {status: 416})
  ]
  const file = await openRemoteFile(async () => answers.shift()!, 'https://a/f')
  await expect(file!.read(0, 10)).rejects.toThrow('HTTP 416')
})
