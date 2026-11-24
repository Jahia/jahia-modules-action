/** Map with an async function, at most `limit` calls at a time, and the results in the order given. */
export const mapLimit = async <T, R>(
  items: T[],
  limit: number,
  mapper: (item: T) => Promise<R>
): Promise<R[]> => {
  const results: R[] = new Array(items.length)
  const worker = async (cursor: {next: number}): Promise<void> => {
    const index = cursor.next++
    if (index >= items.length) return
    results[index] = await mapper(items[index] as T)
    return worker(cursor)
  }
  const cursor = {next: 0}
  await Promise.all(Array.from({length: Math.min(limit, items.length)}, () => worker(cursor)))
  return results
}
