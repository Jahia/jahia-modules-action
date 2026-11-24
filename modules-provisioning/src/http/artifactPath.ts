/** The Maven path of an artifact, of one of its versions, or of a file of that version. */
export const artifactPath = (
  groupId: string,
  artifactId: string,
  version?: string,
  fileName?: string
): string => [groupId.replaceAll('.', '/'), artifactId, version, fileName].filter(Boolean).join('/')
