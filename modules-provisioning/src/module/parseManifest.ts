/** The attributes of a jar manifest, with each continuation line joined to its attribute. */
export const parseManifest = (text: string): Record<string, string> =>
  Object.fromEntries(
    text
      .replaceAll('\r\n', '\n')
      .replaceAll('\n ', '')
      .split('\n')
      .filter(line => line.includes(':'))
      .map(line => [line.slice(0, line.indexOf(':')), line.slice(line.indexOf(':') + 1).trim()])
  )
