import {expect, test, vi} from 'vitest'
import {withRetry} from './withRetry.js'

test('returns the first success, waiting longer each time', async () => {
  const wait = vi.fn(async () => {})
  const operation = vi
    .fn()
    .mockRejectedValueOnce(new Error('one'))
    .mockRejectedValueOnce(new Error('two'))
    .mockResolvedValue('done')
  await expect(withRetry(operation, 3, wait)).resolves.toBe('done')
  expect(wait.mock.calls).toEqual([[2000], [4000]])
})

test('gives up after the last attempt', async () => {
  const wait = vi.fn(async () => {})
  await expect(withRetry(() => Promise.reject(new Error('down')), 2, wait)).rejects.toThrow('down')
  expect(wait).toHaveBeenCalledTimes(1)
})
