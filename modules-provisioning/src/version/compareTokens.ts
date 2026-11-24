import type {VersionToken} from './versionTokens.js'

/**
 * A missing number is 0, so 3.4 is 3.4.0. A qualifier sorts before a number and before nothing, so a
 * snapshot or a beta comes before its release.
 */
export const compareTokens = (left: VersionToken | undefined, right: VersionToken | undefined): number => {
  if (left === right) return 0
  if (typeof left === 'string' && typeof right === 'string') return left < right ? -1 : 1
  if (typeof left === 'string') return -1
  if (typeof right === 'string') return 1
  return Math.sign((left ?? 0) - (right ?? 0))
}
