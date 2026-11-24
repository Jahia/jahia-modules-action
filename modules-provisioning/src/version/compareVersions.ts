import {compareTokens} from './compareTokens.js'
import {versionTokens} from './versionTokens.js'

export const compareVersions = (left: string, right: string): number => {
  const a = versionTokens(left)
  const b = versionTokens(right)
  return (
    Array.from({length: Math.max(a.length, b.length)}, (_, index) => compareTokens(a[index], b[index])).find(
      result => result !== 0
    ) ?? 0
  )
}
