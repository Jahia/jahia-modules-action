/** A tar archive of the given text files, in the order given. */
export const tarOf = (files: [name: string, content: string, prefix?: string][]): Uint8Array => {
  const encoder = new TextEncoder()
  const blocks = files.flatMap(([name, content, prefix = '']) => {
    const data = encoder.encode(content)
    const header = new Uint8Array(512)
    header.set(encoder.encode(name), 0)
    header.set(encoder.encode(data.length.toString(8).padStart(11, '0')), 124)
    header.set(encoder.encode(prefix), 345)
    const body = new Uint8Array(Math.ceil(data.length / 512) * 512)
    body.set(data)
    return [header, body]
  })
  return Uint8Array.from([...blocks, new Uint8Array(1024)].flatMap(block => [...block]))
}
