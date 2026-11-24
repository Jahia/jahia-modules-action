import type {RemoteFile} from '../types.js'

/** A remote file served from memory, which counts the bytes asked of it. */
export const remoteFileOf = (bytes: Uint8Array): RemoteFile & {asked: () => number} => {
  const counter = {bytes: 0}
  return {
    size: bytes.length,
    read: async (start, end) => {
      counter.bytes += Math.max(0, end - start)
      return bytes.subarray(start, end)
    },
    asked: () => counter.bytes
  }
}
