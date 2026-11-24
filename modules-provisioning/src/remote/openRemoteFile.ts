import {isAbsent} from '../http/isAbsent.js'
import type {Http, RemoteFile} from '../types.js'

/**
 * A file read by HTTP ranges, so one entry of a remote jar is read without the jar. Nexus mishandles
 * a suffix range, so the size comes first. A server that ignores ranges, as the proxy of the Store
 * does, answers the whole file, which is then kept.
 */
export const openRemoteFile = async (http: Http, url: string): Promise<RemoteFile | undefined> => {
  const first = await http(url, {Range: 'bytes=0-0'})
  if (isAbsent(first)) return undefined
  if (first.status === 200) {
    const whole = new Uint8Array(await first.arrayBuffer())
    return {size: whole.length, read: async (start, end) => whole.subarray(start, end)}
  }
  const size = Number(/\/(\d+)$/.exec(first.headers.get('Content-Range') ?? '')?.[1])
  if (first.status !== 206 || Number.isNaN(size))
    throw new Error(`${url} serves no byte range (HTTP ${first.status})`)
  return {
    size,
    read: async (start, end) => {
      if (end <= start) return new Uint8Array()
      const response = await http(url, {Range: `bytes=${start}-${end - 1}`})
      if (!response.ok) throw new Error(`${url} answered HTTP ${response.status} to a range`)
      return new Uint8Array(await response.arrayBuffer())
    }
  }
}
