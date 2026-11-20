// One line, cut at a limit: the trace stays readable whatever the agent printed.
export const compact = (value: unknown, limit = 300): string => {
  const text: string | undefined = typeof value === 'string' ? value : JSON.stringify(value)
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- JSON.stringify(undefined) is undefined at runtime, whatever its declared type
  const joined = (text ?? '').split(/\s+/).filter(Boolean).join(' ')
  return joined.length <= limit ? joined : joined.slice(0, limit) + '…'
}
