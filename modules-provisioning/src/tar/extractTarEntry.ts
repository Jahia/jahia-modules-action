import {tarText} from './tarText.js'

/** The bytes of the first entry of a tar archive whose name the predicate accepts. */
export const extractTarEntry = (
  tar: Uint8Array,
  accepts: (name: string) => boolean,
  position = 0
): Uint8Array | undefined => {
  if (position + 512 > tar.length || tar[position] === 0) return undefined
  const header = tar.subarray(position, position + 512)
  const prefix = tarText(header.subarray(345, 500))
  const name = (prefix ? `${prefix}/` : '') + tarText(header.subarray(0, 100))
  const size = parseInt(tarText(header.subarray(124, 136)).trim() || '0', 8)
  const start = position + 512
  return accepts(name)
    ? tar.subarray(start, start + size)
    : extractTarEntry(tar, accepts, start + Math.ceil(size / 512) * 512)
}
