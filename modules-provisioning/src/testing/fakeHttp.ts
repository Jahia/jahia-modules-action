import type {Http} from '../types.js'

type Served = Uint8Array | string | {status: number} | {noRanges: Uint8Array}

/** An Http that serves the given URLs from memory, with byte ranges, and 404 for any other URL. */
export const fakeHttp = (served: Record<string, Served>): Http & {calls: string[]} => {
  const calls: string[] = []
  const http: Http = async (url, headers = {}) => {
    calls.push(url)
    const found = served[url]
    if (found === undefined) return new Response(null, {status: 404})
    if (typeof found === 'object' && 'status' in found) return new Response(null, {status: found.status})
    if (typeof found === 'object' && 'noRanges' in found) return new Response(found.noRanges, {status: 200})
    const bytes = typeof found === 'string' ? new TextEncoder().encode(found) : found
    const range = /bytes=(\d+)-(\d+)/.exec(headers.Range ?? '')
    if (!range) return new Response(bytes, {status: 200})
    const [start, end] = [Number(range[1]), Math.min(Number(range[2]), bytes.length - 1)]
    return new Response(bytes.slice(start, end + 1), {
      status: 206,
      headers: {'Content-Range': `bytes ${start}-${end}/${bytes.length}`}
    })
  }
  return Object.assign(http, {calls})
}
