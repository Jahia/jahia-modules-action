import {expect, test} from 'vitest'
import {mapLimit} from './mapLimit.js'

test('keeps the order, and never runs more than the limit at once', async () => {
  const running = {now: 0, most: 0}
  const results = await mapLimit([30, 5, 20, 1, 10], 2, async delay => {
    running.now += 1
    running.most = Math.max(running.most, running.now)
    await new Promise(resolve => setTimeout(resolve, delay))
    running.now -= 1
    return delay * 2
  })
  expect(results).toEqual([60, 10, 40, 2, 20])
  expect(running.most).toBe(2)
})

test('maps nothing', async () => {
  expect(await mapLimit([], 4, async item => item)).toEqual([])
})
