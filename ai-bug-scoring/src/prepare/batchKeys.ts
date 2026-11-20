// Each batch is one agent run, so a long selection never fills one context.
export const batchKeys = (keys: string[], size: number): string[][] => {
  const bounded = Math.max(1, size)
  const groups: string[][] = []
  for (let start = 0; start < keys.length; start += bounded) {
    groups.push(keys.slice(start, start + bounded))
  }
  return groups
}
