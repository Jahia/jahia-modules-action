// Return a string containing only alphanumerical and -
export const cleanArtifactName = (string: string) => {
  return String(string)
    .replace(/[^a-z0-9\-_+]+/gi, '')
    .toLowerCase()
}
