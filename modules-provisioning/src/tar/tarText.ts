/** A text field of a tar header, which a NUL ends. */
export const tarText = (bytes: Uint8Array): string => new TextDecoder().decode(bytes).replace(/\0.*$/s, '')
