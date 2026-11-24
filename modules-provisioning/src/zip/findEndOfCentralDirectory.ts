export type EndOfCentralDirectory = {size: number; offset: number}

const SIGNATURE = 0x06054b50

/** Where the central directory of a zip is, read from the end of the file. */
export const findEndOfCentralDirectory = (tail: Uint8Array): EndOfCentralDirectory => {
  const view = new DataView(tail.buffer, tail.byteOffset, tail.byteLength)
  const position = Array.from(
    {length: Math.max(0, tail.length - 21)},
    (_, index) => tail.length - 22 - index
  ).find(index => view.getUint32(index, true) === SIGNATURE)
  if (position === undefined) throw new Error('not a zip: no end of central directory')
  return {size: view.getUint32(position + 12, true), offset: view.getUint32(position + 16, true)}
}
