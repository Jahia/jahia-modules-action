// Human-readable duration for the status comment: "45s", "7m 02s", "1h 31m".
export const formatDuration = (totalSeconds: number): string => {
  const seconds = Math.max(0, Math.round(totalSeconds))
  const pad = (n: number): string => String(n).padStart(2, '0')
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  if (hours > 0) return `${String(hours)}h ${pad(minutes)}m`
  if (minutes > 0) return `${String(minutes)}m ${pad(rest)}s`
  return `${String(rest)}s`
}
