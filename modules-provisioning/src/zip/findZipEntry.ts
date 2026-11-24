export type ZipEntry = {name: string; method: number; compressedSize: number; localHeaderOffset: number}

const SIGNATURE = 0x02014b50

/**
 * One entry of the central directory of a zip, found without a list of the others: a jar holds
 * thousands of entries, and only its manifest is wanted.
 */
export const findZipEntry = (directory: Uint8Array, name: string, position = 0): ZipEntry | undefined => {
  const view = new DataView(directory.buffer, directory.byteOffset, directory.byteLength)
  if (position + 46 > directory.length || view.getUint32(position, true) !== SIGNATURE) return undefined
  const nameLength = view.getUint16(position + 28, true)
  const entryName = new TextDecoder().decode(directory.subarray(position + 46, position + 46 + nameLength))
  return entryName === name
    ? {
        name,
        method: view.getUint16(position + 10, true),
        compressedSize: view.getUint32(position + 20, true),
        localHeaderOffset: view.getUint32(position + 42, true)
      }
    : findZipEntry(
        directory,
        name,
        position + 46 + nameLength + view.getUint16(position + 30, true) + view.getUint16(position + 32, true)
      )
}
