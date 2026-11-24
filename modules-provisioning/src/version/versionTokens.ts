export type VersionToken = number | string

/** `4.21.0-jahia8-8` as [4, 21, 0, 'jahia', 8, 8]. */
export const versionTokens = (version: string): VersionToken[] =>
  (version.match(/\d+|[A-Za-z]+/g) ?? []).map(token =>
    /^\d+$/.test(token) ? Number(token) : token.toLowerCase()
  )
