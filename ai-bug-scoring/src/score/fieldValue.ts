import { P1_OFFSET } from './tables'

// The number written to the score field.
export const fieldValue = (points: number, p1: boolean): number =>
  p1 ? points + P1_OFFSET : points
