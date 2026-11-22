// System A2: the points each factor adds — pure data that the validation reads and the scoring
// sums into the field value.

export const IMPACT: Record<string, [number, string]> = {
  data: [40, 'Content loss or data corruption'],
  unstable: [40, 'Erratic in production'],
  siteDown: [40, 'Site fully broken'],
  sitePartial: [30, 'Visitors partly impacted'],
  editorBlocked: [20, 'Editors blocked'],
  devBlocked: [20, 'Developers blocked'],
  hindered: [4, 'Slowed down, not blocked'],
  cosmetic: [1, 'Cosmetic or wording'],
}

// Reach & importance: how many customers use the feature, and how much it matters to them.
export const REACH: Record<string, [number, string]> = {
  veryHigh: [20, 'Very high'],
  high: [15, 'High'],
  medium: [5, 'Medium'],
  low: [0, 'Low'],
  none: [-20, 'None'],
}

export const WORKAROUND: Record<string, number> = { none: 8, painful: 4, unknown: 4, easy: 0 }

export const REGRESSION = 5
export const PER_CUSTOMER = 5
export const MAX_CUSTOMERS = 3
export const CLEAR = 6
export const CLOUD = 3
export const OLDER = -5

// The field value of a security bug: out of scope, and never read again.
export const SECURITY_VALUE = -1

export const CONFIDENCE = new Set(['high', 'medium', 'low'])
