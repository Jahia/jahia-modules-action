import {inflateRawSync} from 'node:zlib'
import {ZIP_TAIL} from '../constants.js'
import type {RemoteFile} from '../types.js'
import {findEndOfCentralDirectory} from './findEndOfCentralDirectory.js'
import {findZipEntry} from './findZipEntry.js'

/** The bytes of one entry of a remote zip, or undefined when the zip has no such entry. */
export const readZipEntry = async (file: RemoteFile, name: string): Promise<Uint8Array | undefined> => {
  const tailStart = Math.max(0, file.size - ZIP_TAIL)
  const tail = await file.read(tailStart, file.size)
  const end = findEndOfCentralDirectory(tail)
  const directory =
    end.offset >= tailStart
      ? tail.subarray(end.offset - tailStart, end.offset - tailStart + end.size)
      : await file.read(end.offset, end.offset + end.size)
  const entry = findZipEntry(directory, name)
  if (entry === undefined) return undefined
  const header = await file.read(entry.localHeaderOffset, entry.localHeaderOffset + 30)
  const view = new DataView(header.buffer, header.byteOffset, header.byteLength)
  const start = entry.localHeaderOffset + 30 + view.getUint16(26, true) + view.getUint16(28, true)
  const data = await file.read(start, start + entry.compressedSize)
  return entry.method === 0 ? data : new Uint8Array(inflateRawSync(data))
}
