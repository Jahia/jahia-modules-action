// System A2: the points each factor adds. Pure data — checkFactors validates against it and
// scoreFactors adds the points.

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

export const P1 = new Set(['data', 'unstable', 'siteDown'])

export const REACH: Record<string, number> = { high: 15, medium: 5, low: 0 }

export const WORKAROUND: Record<string, number> = { none: 8, painful: 4, unknown: 4, easy: 0 }

export const REGRESSION = 5
export const PER_CUSTOMER = 5
export const MAX_CUSTOMERS = 3
export const CLEAR = 6
export const CLOUD = 3
export const OLDER = -5

// The score field holds one number, and A2 sorts every P1 case first: the field adds this to a
// P1 score, so sorting the bugs by the field gives the A2 order.
export const P1_OFFSET = 100

// The field value of a security bug: out of scope, and never read again.
export const SECURITY_VALUE = -1

export const CONFIDENCE = new Set(['high', 'medium', 'low'])
